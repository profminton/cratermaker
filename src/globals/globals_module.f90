!! Copyright 2023 - David Minton
!! This file is part of Cratermaker
!! Cratermaker is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License 
!! as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
!! cratermaker is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty 
!! of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
!! You should have received a copy of the GNU General Public License along with cratermaker. 
!! If not, see: https://www.gnu.org/licenses. 

module globals
   !! author: David A. Minton
   !!
   !! Basic parameters, definitions, and global type definitions used throughout the Swiftest project
   !! Adapted from David E. Kaufmann's Swifter routine: globals.f90 and module_swifter.f90
   use, intrinsic :: iso_fortran_env  ! Use the intrinsic kind definitions
   implicit none
   public

   integer, parameter :: I8B = int64 !! Symbolic name for kind types of 8-byte integers
   integer, parameter :: I4B = int32 !! Symbolic name for kind types of 4-byte integers
   integer, parameter :: I2B = int16 !! Symbolic name for kind types of 2-byte integers
   integer, parameter :: I1B = int8  !! Symbolic name for kind types of 1-byte integers

   integer, parameter :: SP = real32  !! Symbolic name for kind types of single-precision reals
   integer, parameter :: DP = real64  !! Symbolic name for kind types of double-precision reals
#ifdef QUADPREC
   integer, parameter :: QP = selected_Real_kind(30) !! Symbolic name for kind types of quad-precision reals
#else
   integer, parameter :: QP = real64 !! Stick to DP
#endif


   character(*), parameter :: VERSION = "2023.10.0" !! Cratermaker version

end module globals
