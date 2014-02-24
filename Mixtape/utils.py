import json
import numpy as np
from numpy import *
from sklearn.utils import check_random_state
from numpy.linalg import norm
from numpy.random import randint
import mdtraj as md

def iterobjects(fn):
    for line in open(fn, 'r'):
        if line.startswith('#'):
            continue
        try:
            yield json.loads(line)
        except ValueError:
            pass

def load_superpose_timeseries(filenames, atom_indices, topology):
    X = []
    i = []
    f = []
    for file in filenames:
        kwargs = {}  if file.endswith('.h5') else {'top': topology}
        t = md.load(file, **kwargs)
        t.superpose(topology, atom_indices=atom_indices)
        diff2 = (t.xyz[:, atom_indices] - topology.xyz[0, atom_indices])**2
        x = np.sqrt(np.sum(diff2, axis=2))

        X.append(x)
        i.append(np.arange(len(x)))
        f.extend([file]*len(x))

    return np.concatenate(X), np.concatenate(i), np.array(f)


def categorical(pvals, size=None, random_state=None):
    """Return random integer from a categorical distribution

    Parameters
    ----------
    pvals : sequence of floats, length p
        Probabilities of each of the ``p`` different outcomes.  These
        should sum to 1.
    size : int or tuple of ints, optional
        Defines the shape of the returned array of random integers. If None
        (the default), returns a single float.
    random_state: RandomState or an int seed, optional
        A random number generator instance.
    """
    cumsum = np.cumsum(pvals)
    if size is None:
        size = (1,)
        axis = 0
    elif isinstance(size, tuple):
        size = size + (1,)
        axis = len(size) - 1
    else:
        raise TypeError('size must be an int or tuple of ints')

    random_state = check_random_state(random_state)
    return np.sum(cumsum < random_state.random_sample(size), axis=axis)


def iter_vars(A, Q,N):
  V = eye(shape(A)[0])
  for i in range(N):
    V = Q + dot(A,dot(V, A.T))
  return V

def assignment_to_weights(assignments,K):
  (T,) = shape(assignments)
  W_i_Ts = zeros((T,K))
  for t in range(T):
    ind = assignments[t]
    for k in range(K):
      if k != ind:
        W_i_Ts[t,k] = 0.0
      else:
        W_i_Ts[t.__int__(),ind.__int__()] = 1.0
  return W_i_Ts

def empirical_wells(Ys, W_i_Ts):
  (T, y_dim) = shape(Ys)
  (_, K) = shape(W_i_Ts)
  means = zeros((K, y_dim))
  covars = zeros((K, y_dim, y_dim))
  for k in range(K):
    num = zeros(y_dim)
    denom = 0
    for t in range(T):
      num += W_i_Ts[t, k] * Ys[t]
      denom += W_i_Ts[t,k]
    means[k] = (1.0/denom) * num
  for k in range(K):
    num = zeros((y_dim, y_dim))
    denom = 0
    for t in range(T):
      num += W_i_Ts[t, k] * outer(Ys[t] - means[k], Ys[t] - means[k])
      denom += W_i_Ts[t,k]
    covars[k] = (1.0/denom) * num
  return means, covars

def transition_counts(assignments, K):
  (T,) = shape(assignments)
  Zhat = ones((K, K))
  for t in range(1,T):
    i = assignments[t-1]
    j = assignments[t]
    Zhat[i,j] += 1
  for i in range(K):
    s = sum(Zhat[i])
    Zhat[i] /= s
  return Zhat

def kmeans(ys, K):
  """ Takes a dataset and finds the K means through the usual
  k-means algorithm.
  Inputs:
    ys: Dataset of points
    K: number of means
  Outputs:
    means: Learned means
    assigments: Says which mean the t-th datapoint belongs to
  """
  (T, y_dim) = shape(ys)
  means = zeros((K, y_dim))
  old_means = zeros((K, y_dim))
  assignments = zeros(T)
  num_each = zeros(K)
  # Pick random observations as initializations
  for k in range(K):
    r = randint(0,T)
    means[k] = ys[r]
  Delta = Inf
  Epsilon = 1e-5
  iteration = 0
  while Delta >= Epsilon:
    Delta = 0
    # Perform an Assignment Step
    for t in range(T):
      dist = Inf
      y = ys[t]
      # Find closest means
      for k in range(K):
        if norm(y - means[k]) < dist:
          dist = norm(y - means[k])
          assignments[t] = k
    # Perform Mean Update Step
    old_means[:] = means[:]
    # Reset means and num_each
    means[:] = 0
    num_each[:] = 0
    for t in range(T):
      k = assignments[t]
      num_each[k.__int__()] += 1
      means[k.__int__()] += ys[t.__int__()]
    for k in range(K):
      if num_each[k] > 0:
        means[k] /= num_each[k]
      Delta += norm(means[k] - old_means[k])
    # reset numeach
    iteration += 1
  return means, assignments

def means_match(base_means, means, assignments):
  (K, y_dim) = shape(means)
  (T,) = shape(assignments)
  matching = zeros(K)
  new_assignments = zeros(T)
  for i in range(K):
    closest = -1
    closest_dist = Inf
    for j in range(K):
      if norm(base_means[i] - means[j]) < closest_dist:
        closest = j
        #print "base_means[%d] = %s" % (i, str(base_means[i]))
        #print "means[%d] = %s" % (j, str(means[j]))
        closest_dist = norm(base_means[i]- means[j])
    matching[i] = closest
  for t in range(T):
    new_assignments[t] = matching[assignments[t]]
  return matching, new_assignments
