# Copyright 2013-2022 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

from spack.package import *


# Wrapper around depends_on to propagate dependency variants
def dav_sdk_depends_on(spec, when=None, propagate=None):
    # Do the basic depends_on
    depends_on(spec, when=when)

    # Strip spec string to just the base spec name
    # ie. A +c ~b -> A
    spec = Spec(spec).name

    if "+" in when and len(when.split()) == 1:
        when_not = when.replace("+", "~")
        # If the package is in the spec tree then it must
        # be enabled in the SDK.
        conflicts(when_not, "^" + spec)

    # Skip if there is nothing to propagate
    if not propagate:
        return

    # Map the propagated variants to the dependency variant
    if not type(propagate) is dict:
        propagate = dict([(v, v) for v in propagate])

    # Determine the base variant
    base_variant = ""
    if when:
        base_variant = when

    def is_boolean(variant):
        return "=" not in variant

    # Propagate variants to dependecy
    for v_when, v_then in propagate.items():
        if is_boolean(v_when):
            depends_on(
                "{0} +{1}".format(spec, v_then), when="{0} +{1}".format(base_variant, v_when)
            )
            depends_on(
                "{0} ~{1}".format(spec, v_then), when="{0} ~{1}".format(base_variant, v_when)
            )
        else:
            depends_on("{0} {1}".format(spec, v_then), when="{0} {1}".format(base_variant, v_when))


def exclude_variants(variants, exclude):
    return [variant for variant in variants if variant not in exclude]


class EcpDataVisSdk(BundlePackage, CudaPackage, ROCmPackage):
    """ECP Data & Vis SDK"""

    homepage = "https://github.com/chuckatkins/ecp-data-viz-sdk"

    tags = ["ecp"]
    maintainers = ["chuckatkins", "kwryankrattiger"]

    version("1.0")

    ############################################################
    # Variants
    ############################################################

    # I/O
    variant("adios2", default=False, description="Enable ADIOS2")
    variant("darshan", default=False, description="Enable Darshan")
    variant("faodel", default=False, description="Enable FAODEL")
    variant("hdf5", default=False, description="Enable HDF5")
    variant("pnetcdf", default=False, description="Enable PNetCDF")
    variant("unifyfs", default=False, description="Enable UnifyFS")
    variant("veloc", default=False, description="Enable VeloC")

    # Vis
    variant("ascent", default=False, description="Enable Ascent")
    variant("cinema", default=False, description="Enable Cinema")
    variant("paraview", default=False, description="Enable ParaView")
    variant("sensei", default=False, description="Enable Sensei")
    variant("sz", default=False, description="Enable SZ")
    variant("visit", default=False, description="Enable VisIt")
    variant("vtkm", default=False, description="Enable VTK-m")
    variant("zfp", default=False, description="Enable ZFP")

    # Language Options
    variant("fortran", default=True, sticky=True, description="Enable fortran language features.")

    ############################################################
    # Dependencies
    ############################################################
    cuda_arch_variants = ["cuda_arch={0}".format(x) for x in CudaPackage.cuda_arch_values]
    amdgpu_target_variants = ["amdgpu_target={0}".format(x) for x in ROCmPackage.amdgpu_targets]

    dav_sdk_depends_on(
        "adios2+shared+mpi+python+blosc+sst+ssc+dataman",
        when="+adios2",
        propagate=["hdf5", "sz", "zfp", "fortran"],
    )

    dav_sdk_depends_on("darshan-runtime+mpi", when="+darshan", propagate=["hdf5"])
    dav_sdk_depends_on("darshan-util", when="+darshan")

    dav_sdk_depends_on("faodel+shared+mpi network=libfabric", when="+faodel", propagate=["hdf5"])

    dav_sdk_depends_on("hdf5@1.12: +shared+mpi", when="+hdf5", propagate=["fortran"])

    dav_sdk_depends_on("parallel-netcdf+shared", when="+pnetcdf", propagate=["fortran"])

    dav_sdk_depends_on("unifyfs", when="+unifyfs ")

    dav_sdk_depends_on("veloc", when="+veloc")

    propagate_to_sensei = [(v, v) for v in ["adios2", "ascent", "hdf5"]]
    propagate_to_sensei.extend([("paraview", "catalyst"), ("visit", "libsim")])
    dav_sdk_depends_on(
        "sensei@4: ~vtkio +python", when="+sensei", propagate=dict(propagate_to_sensei)
    )

    # Fortran support with ascent is problematic on some Cray platforms so the
    # SDK is explicitly disabling it until the issues are resolved.
    dav_sdk_depends_on(
        "ascent+mpi~fortran+openmp+python+shared+vtkh+dray~test",
        when="+ascent",
        propagate=["adios2", "cuda"] + cuda_arch_variants,
    )
    depends_on("ascent+openmp", when="~rocm+ascent")
    depends_on("ascent~openmp", when="+rocm+ascent")

    # Need to explicitly turn off conduit hdf5_compat in order to build
    # hdf5@1.12 which is required for SDK
    depends_on("ascent ^conduit ~hdf5_compat", when="+ascent +hdf5")
    # Disable configuring with @develop. This should be removed after ascent
    # releases 0.8 and ascent can build with conduit@0.8: and vtk-m@1.7:
    conflicts("ascent@develop", when="+ascent")

    depends_on("py-cinemasci", when="+cinema")

    dav_sdk_depends_on(
        "paraview@5.10:+mpi+python3+kits+shared", when="+paraview", propagate=["hdf5", "adios2"]
    )
    # ParaView needs @5.11: in order to use cuda and be compatible with other
    # SDK packages.
    depends_on("paraview +cuda", when="+paraview +cuda ^paraview@5.11:")
    for cuda_arch in cuda_arch_variants:
        depends_on(
            "paraview {0}".format(cuda_arch),
            when="+paraview {0} ^paraview@5.11:".format(cuda_arch),
        )
    depends_on("paraview ~cuda", when="+paraview ~cuda")
    conflicts("paraview@master", when="+paraview")

    dav_sdk_depends_on("visit+mpi+python+silo", when="+visit", propagate=["hdf5", "adios2"])

    dav_sdk_depends_on(
        "vtk-m@1.7:+shared+mpi+rendering",
        when="+vtkm",
        propagate=["cuda", "rocm"] + cuda_arch_variants + amdgpu_target_variants,
    )
    depends_on("vtk-m+openmp", when="~rocm+vtkm")
    depends_on("vtk-m~openmp", when="+rocm+vtkm")

    # +python is currently broken in sz
    # dav_sdk_depends_on('sz+shared+python+random_access',
    dav_sdk_depends_on("sz+shared+random_access", when="+sz", propagate=["hdf5", "fortran"])

    dav_sdk_depends_on("zfp", when="+zfp", propagate=["cuda"] + cuda_arch_variants)
