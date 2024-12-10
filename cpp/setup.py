# Copyright 2020 DeepMind Technologies Limited.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Build script for the python controller bindings."""

import os
import subprocess
import sys

from setuptools import Extension
from setuptools import setup
from setuptools.command.build_ext import build_ext


PRE_DOWNLOADED_MUJOCO_TAR = "/deps/mujoco-3.1.6-linux-x86_64.tar.gz"

PRE_DOWNLOADED_SOURCE_DIRS = {
    "abseil-cpp": "/deps/abseil-cpp_c2435f8342c2d0ed8101cb43adfd605fdc52dca2",
    "osqp-cpp": "/deps/osqp-cpp_43433736334d6b515ea4b0247156fea9e56c0d3f",
    "osqp": "/deps/osqp_0baddd36bd57ec1cace0a52c6dd9663e8f16df0a",
    "pybind11": "/deps/pybind11_914c06fb252b6cc3727d0eedab6736e88a3fcb01",
    "googletest": "/deps/googletest_e2239ee6043f73722e7aa812a459f54a28552929"
}


class CMakeExtension(Extension):
  """Extension to record the directory to run cmake on."""

  def __init__(self, name, sourcedir, cmake):
    Extension.__init__(self, name, sources=[])
    self.sourcedir = os.path.abspath(sourcedir)
    self.cmake = cmake


class CMakeBuild(build_ext):
  """Runs cmake."""

  def build_extension(self, ext):
    use_preinstalled_libs = (
        os.environ.get("DM_ROBOTICS_USE_PREINSTALLED_LIBRARIES", None)
        is not None)

    output_directory = os.path.abspath(
        os.path.dirname(self.get_ext_fullpath(ext.name)))

    # required for auto-detection of auxiliary "native" libs
    if not output_directory.endswith(os.path.sep):
      output_directory += os.path.sep

    build_type = "Debug" if self.debug else "Release"

    cmake_args = [
        "-DCMAKE_LIBRARY_OUTPUT_DIRECTORY={}".format(output_directory),
        "-DPYTHON_EXECUTABLE={}".format(sys.executable),
        "-DDMR_PYTHON_VERSION={}.{}".format(
            sys.version_info.major, sys.version_info.minor
        ),
        "-DCMAKE_BUILD_TYPE={}".format(build_type),
        "-DDM_ROBOTICS_BUILD_TESTS=OFF",
        "-DDM_ROBOTICS_BUILD_WHEEL=True",
        "--log-level=VERBOSE",
    ]

    if use_preinstalled_libs:
      cmake_args.append("-DDM_ROBOTICS_MUJOCO_TAR={}".format(PRE_DOWNLOADED_MUJOCO_TAR))
      cmake_args.append("-DFETCHCONTENT_FULLY_DISCONNECTED:BOOL=TRUE")
      cmake_args.append("-DDM_ROBOTICS_USE_SYSTEM_Eigen3:BOOL=TRUE")

      for libname, dirname in PRE_DOWNLOADED_SOURCE_DIRS.items():
        if os.path.isdir(dirname):
          cmake_args.append(
              f"-DFETCHCONTENT_SOURCE_DIR_{libname.upper()}:STRING={dirname}")

    build_args = []
    if "CMAKE_BUILD_PARALLEL_LEVEL" not in os.environ:
      build_args += ["-j4"]

    print(f"Cmake build args: {cmake_args}")

    if not os.path.exists(self.build_temp):
      os.makedirs(self.build_temp)

    # Generate build files:
    subprocess.check_call(
        [ext.cmake] + cmake_args + ["-S", ext.sourcedir], cwd=self.build_temp)
    # Build.
    subprocess.check_call(
        [ext.cmake, "--build", "."] + build_args, cwd=self.build_temp)


def _get_requirements(requirements_file):  # pylint: disable=g-doc-args
  """Returns a list of dependencies for setup() from requirements.txt.

  Currently a requirements.txt is being used to specify dependencies. In order
  to avoid specifying it in two places, we're going to use that file as the
  source of truth.

  Lines starting with -r will be ignored. If the requirements are split across
  multiple files, call this function multiple times instead and sum the results.
  """

  def line_should_be_included(line):
    return line and not line.startswith("-r")

  with open(requirements_file) as f:
    return [_parse_line(line) for line in f if line_should_be_included(line)]


def _parse_line(s):
  """Parses a line of a requirements.txt file."""
  requirement, *_ = s.split("#")
  return requirement.strip()


setup(
    name="dm_robotics-controllers",
    package_dir={"dm_robotics.controllers": ""},
    packages=["dm_robotics.controllers"],
    version="0.9.0",
    license="Apache 2.0",
    author="DeepMind",
    description="Python bindings for dm_robotics/cpp/controllers",
    long_description=open("controllers_py/README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/deepmind/dm_robotics/tree/main/cpp/controllers_py",
    python_requires=">=3.7, <3.13",
    setup_requires=["wheel >= 0.31.0"],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries",
        "Topic :: Scientific/Engineering",
    ],
    ext_modules=[
        CMakeExtension(
            "dm_robotics.controllers.cartesian_6d_to_joint_velocity_mapper",
            sourcedir="",
            cmake=os.environ.get("CMAKE_EXE", "cmake"))
    ],
    cmdclass={"build_ext": CMakeBuild},
    zip_safe=False,
)
