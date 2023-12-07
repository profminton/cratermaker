# Copyright 2023 - David Minton
# This file is part of Cratermaker.
# Cratermaker is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License 
# as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# Cratermaker is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty 
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with Cratermaker. 
# If not, see: https://www.gnu.org/licenses. 

SET(CRATERMAKER_BIND fortran_bind)

# Find the Cython executable, but don't look in the cmake root directory (due how cmake and cython are installed on the RCAC system)
FIND_PROGRAM(CYTHON 
            NAMES "cython" 
            NO_CMAKE_PATH
            NO_CMAKE_ENVIRONMENT_PATH
            NO_CMAKE_SYSTEM_PATH
            NO_CMAKE_FIND_ROOT_PATH
            )
MESSAGE(STATUS "Cython executable path: ${CYTHON}")
SET(CYTHON_ARGS "${CMAKE_CURRENT_SOURCE_DIR}/${CRATERMAKER_BIND}.pyx" "--output-file" "${CMAKE_CURRENT_BINARY_DIR}/${CRATERMAKER_BIND}.c")
STRING(TOUPPER "${CMAKE_BUILD_TYPE}" BT)
IF (BT STREQUAL "DEBUG")
    LIST(APPEND CYTHON_ARGS "--gdb")
endif ()
ADD_CUSTOM_COMMAND(
  OUTPUT "${CRATERMAKER_BIND}.c"
  DEPENDS "${CRATERMAKER_BIND}.pyx"
  VERBATIM
  COMMAND "${CYTHON}" ${CYTHON_ARGS} )

PYTHON_ADD_LIBRARY(${CRATERMAKER_BIND} MODULE "${CMAKE_CURRENT_BINARY_DIR}/${CRATERMAKER_BIND}.c" WITH_SOABI)

EXECUTE_PROCESS(
  COMMAND "${Python_EXECUTABLE}"
  -c "import numpy; print(numpy.get_include())"
  OUTPUT_VARIABLE NUMPY_INCLUDE_DIR
  OUTPUT_STRIP_TRAILING_WHITESPACE
)

IF (NOT BUILD_SHARED_LIBS) 
  SET_PROPERTY(TARGET ${CRATERMAKER_BIND} PROPERTY POSITION_INDEPENDENT_CODE)
ENDIF ()
TARGET_LINK_LIBRARIES(${CRATERMAKER_BIND} PUBLIC ${CRATERMAKER_LIBRARY})
TARGET_INCLUDE_DIRECTORIES(${CRATERMAKER_BIND} PUBLIC ${CMAKE_CURRENT_SOURCE_DIR} ${NUMPY_INCLUDE_DIR})

IF (APPLE)
  GET_PROPERTY(current_rpath TARGET ${CRATERMAKER_BIND} PROPERTY INSTALL_RPATH)
  IF(NOT ";${current_rpath};" MATCHES ";@loader_path;")
    SET_PROPERTY(TARGET ${CRATERMAKER_BIND} PROPERTY INSTALL_RPATH "@loader_path")
  ENDIF()

  GET_PROPERTY(current_rpath TARGET ${CRATERMAKER_LIBRARY} PROPERTY INSTALL_RPATH)
  IF(NOT ";${current_rpath};" MATCHES ";@loader_path;")
    SET_PROPERTY(TARGET ${CRATERMAKER_LIBRARY} PROPERTY INSTALL_RPATH "@loader_path")
  ENDIF()
ENDIF()


# Define the install locations
INSTALL(TARGETS ${CRATERMAKER_BIND} ${CRATERMAKER_LIBRARY} LIBRARY DESTINATION ${INSTALL_LIBDIR})