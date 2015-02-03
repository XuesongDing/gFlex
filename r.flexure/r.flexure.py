#! /usr/bin/python
############################################################################
#
# MODULE:       r.flexure
#
# AUTHOR(S):    Andrew Wickert
#
# PURPOSE:      Calculate flexure of the lithosphere under a specified
#               set of loads and with a given elastic thickness (scalar 
#               or array)
#
# COPYRIGHT:    (c) 2012, 2014 Andrew Wickert
#
#               This program is free software under the GNU General Public
#               License (>=v2). Read the file COPYING that comes with GRASS
#               for details.
#
#############################################################################
#
# REQUIREMENTS:
#      -  gFlex: http://csdms.colorado.edu/wiki/gFlex
#         (should be downloaded automatically along with the module)
#         github repository: https://github.com/awickert/gFlex
 
# More information
# Started 11 March 2012 as a GRASS interface for Flexure (now gFlex)
# Revised 15--?? November 2014 after significantly improving the model
# by Andy Wickert

#%module
#% description: Lithospheric flexure
#% keywords: raster
#%end
#%flag
#%  key: l
#%  description: Allows running in lat/lon: dx is f(lat) at grid N-S midpoint
#%end
#%option
#%  key: method
#%  type: string
#%  description: Solution method: Finite Diff. or Superpos. of analytical sol'ns
#%  options: FD, SAS
#%  required : yes
#%end
#%option
#%  key: q0
#%  type: string
#%  gisprompt: old,cell,raster
#%  description: Raster map of loads (thickness * density * g) [Pa]
#%  required : yes
#%end
#%option
#%  key: te
#%  type: string
#%  gisprompt: old,cell,raster
#%  description: Elastic thicnkess: scalar or raster; unis chosen in "te_units"
#%  required : yes
#%end
#%option
#%  key: te_units
#%  type: string
#%  description: Units for elastic thickness
#%  options: m, km
#%  required : yes
#%end
#%option
#%  key: output
#%  type: string
#%  gisprompt: old,cell,raster
#%  description: Output raster map of vertical deflections [m]
#%  required : yes
#%end
#%option
#%  key: solver
#%  type: string
#%  description: Solver type
#%  options: direct, iterative
#%  answer: direct
#%  required : no
#%end
#%option
#%  key: tolerance
#%  type: double
#%  description: Convergence tolerance (between iterations) for iterative solver
#%  answer: 1E-3
#%  required : no
#%end
#%option
#%  key: northbc
#%  type: string
#%  description: Northern boundary condition
#%  options: Dirichlet0, 0Moment0Shear, 0Slope0Shear, Mirror, Periodic, NoOutsideLoads
#%  answer: NoOutsideLoads
#%  required : no
#%end
#%option
#%  key: southbc
#%  type: string
#%  description: Southern boundary condition
#%  options: Dirichlet0, 0Moment0Shear, 0Slope0Shear, Mirror, Periodic, NoOutsideLoads
#%  answer: NoOutsideLoads
#%  required : no
#%end
#%option
#%  key: westbc
#%  type: string
#%  description: Western boundary condition
#%  options: Dirichlet0, 0Moment0Shear, 0Slope0Shear, Mirror, Periodic, NoOutsideLoads
#%  answer: NoOutsideLoads
#%  required : no
#%end
#%option
#%  key: eastbc
#%  type: string
#%  description: Eastern boundary condition
#%  options: Dirichlet0, 0Moment0Shear, 0Slope0Shear, Mirror, Periodic, NoOutsideLoads
#%  answer: NoOutsideLoads
#%  required : no
#%end
#%option
#%  key: g
#%  type: double
#%  description: gravitational acceleration at surface [m/s^2]
#%  answer: 9.8
#%  required : no
#%end
#%option
#%  key: ym
#%  type: double
#%  description: Young's Modulus [Pa]
#%  answer: 65E9
#%  required : no
#%end
#%option
#%  key: nu
#%  type: double
#%  description: Poisson's ratio
#%  answer: 0.25
#%  required : no
#%end
#%option
#%  key: rho_fill
#%  type: double
#%  description: Density of material that fills flexural depressions [kg/m^3]
#%  answer: 0
#%  required : no
#%end
#%option
#%  key: rho_m
#%  type: double
#%  description: Mantle density [kg/m^3]
#%  answer: 3300
#%  required : no
#%end


# GFLEX
import gflex

# PYTHON
import numpy as np
import sys

# GRASS
from grass.script import core as grass
import grass.script.array as garray



import signal
import time


def exit_gracefully(signum, frame):
    # restore the original signal handler as otherwise evil things will happen
    # in raw_input when CTRL+C is pressed, and our signal handler is not re-entrant
    signal.signal(signal.SIGINT, original_sigint)

    try:
        if raw_input("\nReally quit? (y/n)> ").lower().startswith('y'):
            sys.exit(1)

    except KeyboardInterrupt:
        print("Ok ok, quitting")
        sys.exit(1)




def main():

  # This code is for 2D flexural isostasy
  flex = gflex.F2D()
  # And show that it is coming from GRASS GIS
  flex.grass = True
  
  # Flags
  latlon_override = flags['l']
  
  # Inputs
  # Solution selection
  flex.Method = options['method']
  if flex.Method == 'FD':
    flex.Solver = options['solver']
    if flex.Solver:
      flex.ConvergenceTolerance = options['tolerance']
    # Always use the van Wees and Cloetingh (1994) solution type.
    # It is the best.
    flex.PlateSolutionType = 'vWC1994'
  # Parameters that are often changed for the solution
  qs = options['q0']
  flex.qs = garray.array()
  flex.qs.read(qs)
  # Elastic thickness
  try:
    flex.Te = float(options['te'])
  except:
    flex.Te = garray.array() # FlexureTe is the one that is used by Flexure
    flex.Te.read(options['te'])
    flex.Te = np.array(flex.Te)
  if options['te_units'] == 'km':
    flex.Te *= 1000
  elif options['te_units'] == 'm':
    pass
  else:
    sys.exit() # Just do this in case there is a mistake in the options
               # limitations given above
  flex.rho_fill = float(options['rho_fill'])
  # Parameters that often stay at their default values
  flex.g = float(options['g'])
  flex.E = float(options['ym']) # Can't just use "E" because reserved for "east", I think
  flex.nu = float(options['nu'])
  flex.rho_m = float(options['rho_m'])
  # Solver type and iteration tolerance
  flex.Solver = options['solver']
  flex.ConvergenceTolerance = float(options['tolerance'])
  # Boundary conditions
  flex.BC_N = options['northbc']
  flex.BC_S = options['southbc']
  flex.BC_W = options['westbc']
  flex.BC_E = options['eastbc']

  # Set verbosity
  if grass.verbosity() >= 2:
    flex.Verbose = True
  if grass.verbosity() >= 3:
    flex.Debug = True
  elif grass.verbosity() == 0:
    flex.Quiet = True
  
  # First check if output exists
  if len(grass.parse_command('g.list', type='rast', pattern=options['output'])):
    if not grass.overwrite():
      grass.fatal(_("Raster map '" + output + "' already exists. Use '--o' to overwrite."))
  
  # Get grid spacing from GRASS
  # Check if lat/lon and proceed as directed
  if grass.region_env()[6] == '3':
    if latlon_override:
      if flex.Verbose:
        print "Latitude/longitude grid."
        print "Based on r_Earth = 6371 km"
        print "Setting y-resolution [m] to 111,195 * [degrees]"
      flex.dy = grass.region()['nsres']*111195.
      NSmid = (grass.region()['n'] + grass.region()['s'])/2.
      dx_at_mid_latitude = (3.14159/180.) * 6371000. * np.cos(np.deg2rad(NSmid))
      if flex.Verbose:
        print "Setting x-resolution [m] to "+"%.2f" %dx_at_mid_latitude+" * [degrees]"
      flex.dx = grass.region()['ewres']*dx_at_mid_latitude
    else:
      grass.fatal(_("Need the '-l' flag to enable lat/lon solution approximation."))
  # Otherwise straightforward
  else:
    flex.dx = grass.region()['ewres']
    flex.dy = grass.region()['nsres']
    
  """
  # Wish list
  #awickert@dakib:~$ check that lat/lon part of flex code works^C
  #awickert@dakib:~$ find a way to make it cancel-able in mid-run, like it is by itself^C
  #awickert@dakib:~$ perhaps find a way to give it a counter as to how long it will take^C
  #awickert@dakib:~$ or actually, based on my functional relationship, calculate this!
  """

  # CALCULATE!
  flex.initialize()
  flex.run()
  flex.finalize()

  # Write to GRASS
  # Create a new garray buffer and write to it
  outbuffer = garray.array() # Instantiate output buffer
  outbuffer[...] = flex.w
  outbuffer.write(options['output'], overwrite=grass.overwrite) # Write it with the desired name
  # And create a nice colormap!
  grass.run_command('r.colors', map=options['output'], color='differences', quiet=True)

  # Reinstate this with a flag or output filename
  # But I think better to let interpolation happen a posteriori
  # So the user knows what the solution is and what it isn't
  #grass.run_command('r.resamp.interp', input=output, output=output + '_interp', method='lanczos', overwrite=True, quiet=True)
  #grass.run_command('r.colors', map=output + '_interp', color='rainbow', quiet=True)#, flags='e')

if __name__ == "__main__":
  options, flags = grass.parser()
  #original_sigint = signal.getsignal(signal.SIGINT)
  #signal.signal(signal.SIGINT, exit_gracefully)
  try:
    main()
  except:
    sys.exit()
