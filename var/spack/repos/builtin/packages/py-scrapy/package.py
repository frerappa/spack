# Copyright 2013-2022 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

# ----------------------------------------------------------------------------
# If you submit this package back to Spack as a pull request,
# please first remove this boilerplate and all FIXME comments.
#
# This is a template package file for Spack.  We've put "FIXME"
# next to all the things you'll want to change. Once you've handled
# them, you can save this file and test your package like this:
#
#     spack install py-scrapy
#
# You can edit this file again by typing:
#
#     spack edit py-scrapy
#
# See the Spack documentation for more information on packaging.
# ----------------------------------------------------------------------------

from spack.package import *


class PyScrapy(PythonPackage):
    """Scrapy is a fast high-level web crawling and web scraping framework, 
    used to crawl websites and extract structured data from their pages. 
    It can be used for a wide range of purposes, from data mining to monitoring and automated testing."""

    homepage = "https://scrapy.org/"
    url = "https://github.com/scrapy/scrapy/archive/refs/tags/2.6.2.tar.gz"


    maintainers = ["frerappa"]

    version("2.6.2", sha256="64334f0bd0c4ea695205656ed004b562af146fa541f157dc4efa4a9096987e9e")

    depends_on("py-lxml", type=("build", "run"))

    # FIXME: Only add the python/pip/wheel dependencies if you need specific versions
    # or need to change the dependency type. Generic python/pip/wheel dependencies are
    # added implicity by the PythonPackage base class.
    # depends_on("python@2.X:2.Y,3.Z:", type=("build", "run"))
    # depends_on("py-pip@X.Y:", type="build")
    # depends_on("py-wheel@X.Y:", type="build")

    # FIXME: Add a build backend, usually defined in pyproject.toml. If no such file
    # exists, use setuptools.
    # depends_on("py-setuptools", type="build")
    # depends_on("py-flit-core", type="build")
    # depends_on("py-poetry-core", type="build")

    # FIXME: Add additional dependencies if required.
    # depends_on("py-foo", type=("build", "run"))

    # def global_options(self, spec, prefix):
    #     # FIXME: Add options to pass to setup.py
    #     # FIXME: If not needed, delete this function
    #     options = []
    #     return options

    # def install_options(self, spec, prefix):
    #     # FIXME: Add options to pass to setup.py install
    #     # FIXME: If not needed, delete this function
    #     options = []
    #     return options
