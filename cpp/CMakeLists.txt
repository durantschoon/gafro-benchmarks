# SPDX-FileCopyrightText: Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Tobias Loew <tobias.loew@idiap.ch>
# SPDX-FileContributor: Durant Schoon <durant.schoon@gmail.com>
#
# SPDX-License-Identifier: MPL-2.0

cmake_minimum_required(VERSION 3.20)
project(gafro_cpp_benchmarks CXX)

set(CMAKE_CXX_STANDARD 26)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(GAFRO_CPP_DIR "${CMAKE_CURRENT_LIST_DIR}/../../gafro-cpp")

find_package(Eigen3 REQUIRED)

add_executable(bench_cga_cpp bench_cga.cpp)

target_include_directories(bench_cga_cpp PRIVATE
    "${GAFRO_CPP_DIR}/include"
    "${GAFRO_CPP_DIR}/src"
    "${GAFRO_CPP_DIR}/build/src"
    ${EIGEN3_INCLUDE_DIR}
)

target_link_libraries(bench_cga_cpp PRIVATE
    Eigen3::Eigen
)

target_compile_options(bench_cga_cpp PRIVATE
    -O3
    -march=native
    -Wno-deprecated-declarations
)
