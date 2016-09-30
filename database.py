import numpy as np
class Database:
   def __init__(self, filename):
      self._filename = filename

   # Number of days
   def days(self):
      return 10

   # Number of trajectories
   def size(self):
      return 3000

   def vars(self):
         return ["T"]

   def get(self, index):
      data = dict()

      T = self.days()
      for var in self.vars():
         #data[var] = np.cumsum(np.random.randn(T))/np.sqrt(range(1, T+1))
         #data[var] = np.cumsum(np.random.randn(T))*np.exp(-0.01*np.linspace(0, T, T))
         data[var] = np.random.randn(1)*1+ np.cumsum(np.random.randn(T))
      return data


   
