import inspect
import netCDF4
import matplotlib.pylab as mpl
import numpy as np
import sys
import wxgen.util
import matplotlib.dates


def get_all():
   """ Returns a list of all output classes """
   temp = inspect.getmembers(sys.modules[__name__], inspect.isclass)
   return temp


def get(name):
   """ Returns an output object of a class with the given name """
   outputs = get_all()
   m = None
   for mm in outputs:
      if(name == mm[0].lower()):
         m = mm[1]
   if m is None:
      wxgen.util.error("Cannot find output called '%s'" % name)
   return m


class Output(object):
   """
   A class for outputing trajectory information
   """
   def __init__(self, db):
      self.filename = None
      self._db = db
      self.dpi = 300
      self.fig_size = [10,5]
      self.xlim = None
      self.ylim = None
      self.xlog = False
      self.ylog = False
      self.xticks = None
      self.yticks = None
      self.xticklabels = None
      self.yticklabels = None
      self._sets_xticks = None
      self._sets_yticks = None

   def _finish_plot(self):
      if self.xlim is not None:
         mpl.xlim(self.xlim)
      if self.ylim is not None:
         mpl.ylim(self.ylim)
      if self.xlog:
         # Keep tany set ticks and labels
         if self._sets_xticks:
            xticks = mpl.gca().get_xticks()
            xticklabels = mpl.gca().get_xticklabels()
         mpl.gca().set_xscale("log")
         if self._sets_xticks:
            mpl.gca().set_xticks(xticks)
            mpl.gca().set_xticklabels(xticklabels)
      if self.ylog:
         if self._sets_yticks:
            yticks = mpl.gca().get_yticks()
            yticklabels = mpl.gca().get_yticklabels()
         mpl.gca().set_yscale("log")
         if self._sets_yticks:
            mpl.gca().set_yticks(yticks)
            mpl.gca().set_yticklabels(yticklabels)
      if self.filename is None:
         mpl.show()
      else:
         mpl.gcf().set_size_inches(self.fig_size[0],self.fig_size[1])
         mpl.savefig(self.filename, bbox_inches='tight', dpi=self.dpi)


class Timeseries(Output):
   """
   Draws all trajectories as lines. One variable per subplot.
   """
   def plot(self, trajectories):
      T = trajectories[0].length
      V = len(trajectories[0].variables)
      variables = trajectories[0].variables
      Tsegment = self._db.length
      for v in range(0, V):
         mpl.subplot(V,1,v+1)
         start_date = matplotlib.dates.date2num(matplotlib.dates.datetime.datetime(2017, 1, 1, 0))
         x = start_date + np.linspace(0, T-1, T)
         for tr in trajectories:
            values = tr.extract()
            # Plot the trajectory
            assert(np.sum(np.isnan(values)) == 0)
            mpl.plot(x, values[:,v], '-', lw=1)

            # Plot the starting state of each segment
            #I = range(0, T, Tsegment-1)
            #mpl.plot(x[I], tr[I,v], 'ko', mfc='w')

         label = variables[v].pretty() #"%s (%s)" % (variables[v].label, variables[v].units)
         mpl.ylabel(label)
         mpl.grid()
        
         mpl.gca().xaxis_date()
         if np.max(x) - np.min(x) < 100:
            locator = matplotlib.ticker.FixedLocator(np.arange(np.min(x), np.max(x), Tsegment-1))
            # locator = matplotlib.ticker.MultipleLocator(Tsegment-1)
            formatter = matplotlib.dates.DateFormatter('%Y-%m-%d')
            mpl.gca().xaxis.set_major_locator(locator)
            mpl.gca().xaxis.set_major_formatter(formatter)
         if v != V-1:
            mpl.gca().set_xticklabels([])
         mpl.xlim(np.min(x), np.max(x))
      mpl.xlabel("Date")
      self._finish_plot()


class Variance(Output):
   def __init__(self, db):
      Output. __init__(self, db)
      self._timescales = np.array([1, 7, 30, 365])
      self._timescales = np.arange(1, 365)
      #self._timescales_names = ["day", "week", "month", "year"]
      self._sets_xticks = True
      self._sets_yticks = False

   def plot(self, trajectories):
      truth = self._db.get_truth()
      variables = self._db.variables
      V = len(variables)
      for v in range(V):
         mpl.subplot(V,1,v+1)
         x, y_obs, y_fcst = self.compute(truth, trajectories)
         xx = range(len(self._timescales))
         mpl.plot(x, y_obs[:,v], '-', lw=3, label='True')
         mpl.plot(x, y_fcst[:,v], '-', lw=3, label='Simulated')
         mpl.gca().set_xticks([1,7,30,365])
         mpl.gca().set_xticklabels(["day", "week", "month", "year"])
         mpl.xlabel("Time scale")
         mpl.ylabel("Variance ($%s^2$)" % variables[v].units)
         #ylim = [0, mpl.ylim()[1]]
         #mpl.ylim(ylim)
         mpl.grid()
         mpl.legend()
      self._finish_plot()

   def compute(self, truth, trajectories):
      S = len(self._timescales)
      V = len(self._db.variables)
      obs_variance = np.zeros([S, V], float)
      fcst_variance = np.zeros([S,V], float)
      fcst = np.zeros([trajectories[0].length, len(trajectories[0].variables), len(trajectories)])
      obs0 = truth.extract()
      obs = np.zeros([365, obs0.shape[1], np.ceil(obs0.shape[0]/365)])
      for i in range(0, int(np.ceil(obs0.shape[0]/365))):
         I = range(i*365, (i+1)*365)
         obs[:,:,i] = obs0[I,:]
      for t in range(0, len(trajectories)):
         fcst[:, :, t] = trajectories[t].extract()
      clim = np.nanmean(obs, axis=2)
      for i in range(0, obs.shape[2]):
         obs[:,:,i] = obs[:,:,i] - clim
      for i in range(0, fcst.shape[2]):
         fcst[:,:,i] = fcst[:,:,i] - clim

      for v in range(0, V):
         for i in range(0, len(self._timescales)):
            s = self._timescales[i]
            c = [1.0/s]* s
            obs_c = np.zeros([obs.shape[0], obs.shape[2]], float)
            for e in range(0, obs.shape[2]):
               obs_c[:,e] = np.convolve(obs[:,v,e], c, 'same')
            obs_variance[i,v] = np.nanvar(obs_c)

            fcst_c = np.zeros([fcst.shape[0], fcst.shape[2]], float)
            for e in range(0, fcst.shape[2]):
               fcst_c[:,e] = np.convolve(fcst[:,v,e], c, 'same')
            fcst_variance[i,v] = np.nanvar(fcst_c)

      return self._timescales, obs_variance, fcst_variance


class Text(Output):
   """
   Writes the trajectories to a text file. One variable in each column and each day on a separate
   line. Trajectories are separated by a blank line.
   """
   def plot(self, trajectories):
      if self.filename is None:
         wxgen.util.error("Text output requires a filename")

      fid = open(self.filename, "w")
      N = len(trajectories)
      T = trajectories[0].length
      V = len(trajectories[0].variables)
      for n in range(0, N):
         values = trajectories[n].extract()
         for t in range(0, T):
            for v in range(0, V):
               fid.write("%f " % values[t,v])
            fid.write("\n")
         if n < N-1:
            fid.write("\n")
      fid.close()


class Netcdf(Output):
   """
   Writes the trajectories to a netcdf file.
   """
   def plot(self, trajectories):
      if self.filename is None:
         wxgen.util.error("Netcdf output requires a filename")
      file = netCDF4.Dataset(self.filename, 'w')


      variables = trajectories[0].variables
      fid = open(self.filename, "w")
      file.createDimension("time")
      file.createDimension("ensemble_member", len(trajectories))
      file.createDimension("lat", trajectories[0].Y)
      file.createDimension("lon", trajectories[0].X)

      var_lat = file.createVariable("lat", "f4", ("lat"))
      var_lon = file.createVariable("lon", "f4", ("lon"))
      var_lat[:] = trajectories[0].database.lats
      var_lon[:] = trajectories[0].database.lons
      vars = dict()
      for var in variables:
         vars[var.name] = file.createVariable(var.name, "f4", ("time", "ensemble_member", "lat", "lon"))

      for m in range(0, len(trajectories)):
         values = trajectories[m].extract_grid()
         values = np.expand_dims(values,1)
         for v in range(0, len(variables)):
            vars[variables[v].name][:,m,:,:] = values[:,:,:,:,v]

      file.close()


class Verification(Output):
   """
   Plots verification data for the trajectories.
   """
   _pool = True
   def plot(self, trajectories):
      N = len(trajectories)
      T = trajectories[0].shape[0]
      V = trajectories[0].shape[1]
      Tsegment = self._db.days()
      variables = self._db.variables
      if self._pool:
         size = Tsegment-1
         x = np.linspace(0, Tsegment-2, Tsegment-1)
      else:
         size = T
         x = np.linspace(0, T-1, T)
      changes = np.zeros(size, float)
      counter = np.zeros(size, int)
      for v in range(0, V):
         mpl.subplot(V, 1, v+1)
         mpl.title(variables[v].name)
         for t in range(0, T-1):
            ar = np.array([abs(trajectories[i][t,v] - trajectories[i][t+1,v]) for i in range(0, N)])
            if self._pool:
               I = t % (Tsegment-1)  # use this to pool similar leadtimes
            else:
               I = t
            changes[I] = changes[I] + np.mean(ar)
            counter[I] = counter[I] + 1
         mpl.plot(x, changes / counter, 'k-')
         mpl.xlabel("Day")
         mpl.ylabel("Average absolute change to next day")
         mpl.grid()
         mpl.xlim([0, size])
         ylim = mpl.ylim()
         mpl.ylim([0, ylim[1]])
      self._finish_plot()

