# Copyright 2013-2022 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

import os
import stat

import pytest

import spack.config
import spack.package_prefs
import spack.repo
import spack.util.spack_yaml as syaml
from spack.config import ConfigError
from spack.spec import Spec
from spack.version import Version


@pytest.fixture()
def configure_permissions():
    conf = syaml.load_config(
        """\
all:
  permissions:
    read: group
    write: group
    group: all
mpich:
  permissions:
    read: user
    write: user
mpileaks:
  permissions:
    write: user
    group: mpileaks
callpath:
  permissions:
    write: world
"""
    )
    spack.config.set("packages", conf, scope="concretize")

    yield


def concretize(abstract_spec):
    return Spec(abstract_spec).concretized()


def update_packages(pkgname, section, value):
    """Update config and reread package list"""
    conf = {pkgname: {section: value}}
    spack.config.set("packages", conf, scope="concretize")


def assert_variant_values(spec, **variants):
    concrete = concretize(spec)
    for variant, value in variants.items():
        assert concrete.variants[variant].value == value


@pytest.mark.usefixtures("concretize_scope", "mock_packages")
class TestConcretizePreferences(object):
    @pytest.mark.parametrize(
        "package_name,variant_value,expected_results",
        [
            (
                "mpileaks",
                "~debug~opt+shared+static",
                {"debug": False, "opt": False, "shared": True, "static": True},
            ),
            # Check that using a list of variants instead of a single string works
            (
                "mpileaks",
                ["~debug", "~opt", "+shared", "+static"],
                {"debug": False, "opt": False, "shared": True, "static": True},
            ),
            # Use different values for the variants and check them again
            (
                "mpileaks",
                ["+debug", "+opt", "~shared", "-static"],
                {"debug": True, "opt": True, "shared": False, "static": False},
            ),
            # Check a multivalued variant with multiple values set
            (
                "multivalue-variant",
                ["foo=bar,baz", "fee=bar"],
                {"foo": ("bar", "baz"), "fee": "bar"},
            ),
            ("singlevalue-variant", ["fum=why"], {"fum": "why"}),
        ],
    )
    def test_preferred_variants(self, package_name, variant_value, expected_results):
        """Test preferred variants are applied correctly"""
        update_packages(package_name, "variants", variant_value)
        assert_variant_values(package_name, **expected_results)

    def test_preferred_variants_from_wildcard(self):
        """
        Test that 'foo=*' concretizes to any value
        """
        update_packages("multivalue-variant", "variants", "foo=bar")
        assert_variant_values("multivalue-variant foo=*", foo=("bar",))

    def test_preferred_compilers(self):
        """Test preferred compilers are applied correctly"""
        # Need to make sure the test uses an available compiler
        compiler_list = spack.compilers.all_compiler_specs()
        assert compiler_list

        # Try the first available compiler
        compiler = str(compiler_list[0])
        update_packages("mpileaks", "compiler", [compiler])
        spec = concretize("mpileaks")
        assert spec.compiler == spack.spec.CompilerSpec(compiler)

        # Try the last available compiler
        compiler = str(compiler_list[-1])
        update_packages("mpileaks", "compiler", [compiler])
        spec = concretize("mpileaks os=redhat6")
        assert spec.compiler == spack.spec.CompilerSpec(compiler)

    def test_preferred_target(self, mutable_mock_repo):
        """Test preferred targets are applied correctly"""
        # FIXME: This test was a false negative, since the default and
        # FIXME: the preferred target were the same
        if spack.config.get("config:concretizer") == "original":
            pytest.xfail("Known bug in the original concretizer")

        spec = concretize("mpich")
        default = str(spec.target)
        preferred = str(spec.target.family)

        update_packages("mpich", "target", [preferred])
        spec = concretize("mpich")
        assert str(spec.target) == preferred

        spec = concretize("mpileaks")
        assert str(spec["mpileaks"].target) == preferred
        assert str(spec["mpich"].target) == preferred

        update_packages("mpileaks", "target", [default])
        spec = concretize("mpileaks")
        assert str(spec["mpileaks"].target) == default
        assert str(spec["mpich"].target) == default

    def test_preferred_versions(self):
        """Test preferred package versions are applied correctly"""
        update_packages("mpileaks", "version", ["2.3"])
        spec = concretize("mpileaks")
        assert spec.version == Version("2.3")

        update_packages("mpileaks", "version", ["2.2"])
        spec = concretize("mpileaks")
        assert spec.version == Version("2.2")

    def test_preferred_versions_mixed_version_types(self):
        update_packages("mixedversions", "version", ["2.0"])
        spec = concretize("mixedversions")
        assert spec.version == Version("2.0")

    def test_preferred_providers(self):
        """Test preferred providers of virtual packages are
        applied correctly
        """
        update_packages("all", "providers", {"mpi": ["mpich"]})
        spec = concretize("mpileaks")
        assert "mpich" in spec

        update_packages("all", "providers", {"mpi": ["zmpi"]})
        spec = concretize("mpileaks")
        assert "zmpi" in spec

    def test_preferred(self):
        """ "Test packages with some version marked as preferred=True"""
        spec = Spec("python")
        spec.concretize()
        assert spec.version == Version("2.7.11")

        # now add packages.yaml with versions other than preferred
        # ensure that once config is in place, non-preferred version is used
        update_packages("python", "version", ["3.5.0"])
        spec = Spec("python")
        spec.concretize()
        assert spec.version == Version("3.5.0")

    def test_develop(self):
        """Test concretization with develop-like versions"""
        spec = Spec("develop-test")
        spec.concretize()
        assert spec.version == Version("0.2.15")
        spec = Spec("develop-test2")
        spec.concretize()
        assert spec.version == Version("0.2.15")

        # now add packages.yaml with develop-like versions
        # ensure that once config is in place, develop-like version is used
        update_packages("develop-test", "version", ["develop"])
        spec = Spec("develop-test")
        spec.concretize()
        assert spec.version == Version("develop")

        update_packages("develop-test2", "version", ["0.2.15.develop"])
        spec = Spec("develop-test2")
        spec.concretize()
        assert spec.version == Version("0.2.15.develop")

    def test_external_mpi(self):
        # make sure this doesn't give us an external first.
        spec = Spec("mpi")
        spec.concretize()
        assert not spec["mpi"].external

        # load config
        conf = syaml.load_config(
            """\
all:
    providers:
        mpi: [mpich]
mpich:
    buildable: false
    externals:
    - spec: mpich@3.0.4
      prefix: /dummy/path
"""
        )
        spack.config.set("packages", conf, scope="concretize")

        # ensure that once config is in place, external is used
        spec = Spec("mpi")
        spec.concretize()
        assert spec["mpich"].external_path == os.sep + os.path.join("dummy", "path")

    def test_external_module(self, monkeypatch):
        """Test that packages can find externals specified by module

        The specific code for parsing the module is tested elsewhere.
        This just tests that the preference is accounted for"""
        # make sure this doesn't give us an external first.
        def mock_module(cmd, module):
            return "prepend-path PATH /dummy/path"

        monkeypatch.setattr(spack.util.module_cmd, "module", mock_module)

        spec = Spec("mpi")
        spec.concretize()
        assert not spec["mpi"].external

        # load config
        conf = syaml.load_config(
            """\
all:
    providers:
        mpi: [mpich]
mpi:
    buildable: false
    externals:
    - spec: mpich@3.0.4
      modules: [dummy]
"""
        )
        spack.config.set("packages", conf, scope="concretize")

        # ensure that once config is in place, external is used
        spec = Spec("mpi")
        spec.concretize()
        assert spec["mpich"].external_path == "/dummy/path"

    def test_buildable_false(self):
        conf = syaml.load_config(
            """\
libelf:
  buildable: false
"""
        )
        spack.config.set("packages", conf, scope="concretize")
        spec = Spec("libelf")
        assert not spack.package_prefs.is_spec_buildable(spec)

        spec = Spec("mpich")
        assert spack.package_prefs.is_spec_buildable(spec)

    def test_buildable_false_virtual(self):
        conf = syaml.load_config(
            """\
mpi:
  buildable: false
"""
        )
        spack.config.set("packages", conf, scope="concretize")
        spec = Spec("libelf")
        assert spack.package_prefs.is_spec_buildable(spec)

        spec = Spec("mpich")
        assert not spack.package_prefs.is_spec_buildable(spec)

    def test_buildable_false_all(self):
        conf = syaml.load_config(
            """\
all:
  buildable: false
"""
        )
        spack.config.set("packages", conf, scope="concretize")
        spec = Spec("libelf")
        assert not spack.package_prefs.is_spec_buildable(spec)

        spec = Spec("mpich")
        assert not spack.package_prefs.is_spec_buildable(spec)

    def test_buildable_false_all_true_package(self):
        conf = syaml.load_config(
            """\
all:
  buildable: false
libelf:
  buildable: true
"""
        )
        spack.config.set("packages", conf, scope="concretize")
        spec = Spec("libelf")
        assert spack.package_prefs.is_spec_buildable(spec)

        spec = Spec("mpich")
        assert not spack.package_prefs.is_spec_buildable(spec)

    def test_buildable_false_all_true_virtual(self):
        conf = syaml.load_config(
            """\
all:
  buildable: false
mpi:
  buildable: true
"""
        )
        spack.config.set("packages", conf, scope="concretize")
        spec = Spec("libelf")
        assert not spack.package_prefs.is_spec_buildable(spec)

        spec = Spec("mpich")
        assert spack.package_prefs.is_spec_buildable(spec)

    def test_config_permissions_from_all(self, configure_permissions):
        # Although these aren't strictly about concretization, they are
        # configured in the same file and therefore convenient to test here.
        # Make sure we can configure readable and writable

        # Test inheriting from 'all'
        spec = Spec("zmpi")
        perms = spack.package_prefs.get_package_permissions(spec)
        assert perms == stat.S_IRWXU | stat.S_IRWXG

        dir_perms = spack.package_prefs.get_package_dir_permissions(spec)
        assert dir_perms == stat.S_IRWXU | stat.S_IRWXG | stat.S_ISGID

        group = spack.package_prefs.get_package_group(spec)
        assert group == "all"

    def test_config_permissions_from_package(self, configure_permissions):
        # Test overriding 'all'
        spec = Spec("mpich")
        perms = spack.package_prefs.get_package_permissions(spec)
        assert perms == stat.S_IRWXU

        dir_perms = spack.package_prefs.get_package_dir_permissions(spec)
        assert dir_perms == stat.S_IRWXU

        group = spack.package_prefs.get_package_group(spec)
        assert group == "all"

    def test_config_permissions_differ_read_write(self, configure_permissions):
        # Test overriding group from 'all' and different readable/writable
        spec = Spec("mpileaks")
        perms = spack.package_prefs.get_package_permissions(spec)
        assert perms == stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP

        dir_perms = spack.package_prefs.get_package_dir_permissions(spec)
        expected = stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_ISGID
        assert dir_perms == expected

        group = spack.package_prefs.get_package_group(spec)
        assert group == "mpileaks"

    def test_config_perms_fail_write_gt_read(self, configure_permissions):
        # Test failure for writable more permissive than readable
        spec = Spec("callpath")
        with pytest.raises(ConfigError):
            spack.package_prefs.get_package_permissions(spec)

    @pytest.mark.regression("20040")
    def test_variant_not_flipped_to_pull_externals(self):
        """Test that a package doesn't prefer pulling in an
        external to using the default value of a variant.
        """
        s = Spec("vdefault-or-external-root").concretized()

        assert "~external" in s["vdefault-or-external"]
        assert "externaltool" not in s

    @pytest.mark.regression("25585")
    def test_dependencies_cant_make_version_parent_score_better(self):
        """Test that a package can't select a worse version for a
        dependent because doing so it can pull-in a dependency
        that makes the overall version score even or better and maybe
        has a better score in some lower priority criteria.
        """
        s = Spec("version-test-root").concretized()

        assert s.satisfies("^version-test-pkg@2.4.6")
        assert "version-test-dependency-preferred" not in s

    @pytest.mark.regression("26598")
    def test_multivalued_variants_are_lower_priority_than_providers(self):
        """Test that the rule to maximize the number of values for multivalued
        variants is considered at lower priority than selecting the default
        provider for virtual dependencies.

        This ensures that we don't e.g. select openmpi over mpich even if we
        specified mpich as the default mpi provider, just because openmpi supports
        more fabrics by default.
        """
        with spack.config.override(
            "packages:all", {"providers": {"somevirtual": ["some-virtual-preferred"]}}
        ):
            s = Spec("somevirtual").concretized()
            assert s.name == "some-virtual-preferred"

    @pytest.mark.regression("26721,19736")
    def test_sticky_variant_accounts_for_packages_yaml(self):
        with spack.config.override("packages:sticky-variant", {"variants": "+allow-gcc"}):
            s = Spec("sticky-variant %gcc").concretized()
            assert s.satisfies("%gcc") and s.satisfies("+allow-gcc")
