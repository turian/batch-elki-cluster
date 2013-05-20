#!/usr/bin/python
"""
Batch invoke ELKI clustering.

TODO:
    * There are a handful of other ELKI clustering algorithms that I didn't include.
"""

import argparse
from collections import OrderedDict
import itertools
import os
import sys
import random
import popen2
import string
import os.path
import glob
import re

random.seed(2)

from render import render

OVERALLPARAMS = "-algorithm.distancefunction EuclideanDistanceFunction"
#OVERALLPARAMS = "-algorithm.distancefunction correlation.PearsonCorrelationDistanceFunction"
NCLUSTERS = [1, 2, 3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 24, 28, 32, 36, 40]
#NCLUSTERS = [1, 2, 3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 24, 28]
#NCLUSTERS = [1, 2, 3, 4, 5]
HYPERPARAMS = OrderedDict({
    "clustering.DBSCAN":
        OrderedDict({
            "dbscan.epsilon": [0.1, 0.25, 0.5, 0.75, 0.9],
            "dbscan.minpts": [5, 50],
        }),
    "clustering.DeLiClu":
        OrderedDict({
            "deliclu.minpts": [5, 50],
        }),
#   # Doesn't work for me, I keep getting NaN
#    "clustering.EM":
#        OrderedDict({
#            "em.k": NCLUSTERS,
#        }),
#   # Slow
#    "clustering.NaiveMeanShiftClustering":
#        OrderedDict({
#            "meanshift.kernel-bandwidth": [0.1, 0.25, 0.5, 0.75, 0.9],
#        }),
#   # Not meant to be run by itself
#    "clustering.OPTICS":
#        OrderedDict({
#            "optics.epsilon": [0.1, 0.25, 0.5, 0.75, 0.9],
#            "optics.minpts": [5, 50],
#        }),
#   # I don't want to code an inner loop for producing hyperparameters for each algorithm.
#    "clustering.OPTICSXi":
#        OrderedDict({
#            "opticsxi.xi": [0.1, 0.25, 0.5, 0.75, 0.9],
#            "opticsxi.algorithm": ["OPTICS", "DeLiClu", "correlation.HiCO", "subspace.HiSC"],
#        }),
#   # Different cluster file format
#    "clustering.SLINK":
#        OrderedDict({
#        }),
#   # This doesn't work for me
#    "clustering.SNNClustering":
#        OrderedDict({
#            "snn.epsilon": [0.1, 0.25, 0.5, 0.75, 0.9],
#            "snn.minpts": [5, 50],
#        }),
    "clustering.gdbscan.GeneralizedDBSCAN":
        OrderedDict({
            "dbscan.epsilon": [0.1, 0.25, 0.5, 0.75, 0.9],
            "dbscan.minpts": [5, 50],
        }),
    "clustering.kmeans.KMeansLloyd":
        OrderedDict({
            "kmeans.k": NCLUSTERS,
            "kmeans.initialization": ["KMeansPlusPlusInitialMeans"],
        }),
    "clustering.kmeans.KMeansMacQueen":
        OrderedDict({
            "kmeans.k": NCLUSTERS,
            "kmeans.initialization": ["KMeansPlusPlusInitialMeans"],
        }),
#    # This can be VERY slow
#    "clustering.kmeans.KMediansLloyd":
#        OrderedDict({
#            "kmeans.k": NCLUSTERS,
#            "kmeans.initialization": ["KMeansPlusPlusInitialMeans"],
#        }),
#    "clustering.kmeans.KMedoidsEM":
#        OrderedDict({
#            "kmeans.k": NCLUSTERS,
#            "kmeans.initialization": ["KMeansPlusPlusInitialMeans"],
#        }),
#    # This can be slow
#    "clustering.kmeans.KMedoidsPAM":
#        OrderedDict({
#            "kmeans.k": NCLUSTERS,
#            "kmeans.initialization": ["KMeansPlusPlusInitialMeans"],
#        }),
})

def tsne(args):
    # Convert CSV to TSV for tSNE
    (child_stdout, child_stdin) = popen2.popen2("sed 1d %s | perl -ne 's/,/\t/g; print' | ./barnes-hut-sne/bhtsne.py" % args.infile)
    points = []
    for l in child_stdout:
        points.append([float(i) for i in string.split(l)])
    return points

def cluster(args, points):
    cmds = []
    for algorithm in HYPERPARAMS:
        hyperparams = list(itertools.product(*HYPERPARAMS[algorithm].values()))
        for h in hyperparams:
            params = zip(HYPERPARAMS[algorithm].keys(), h)
            pstr = ""
            algparam = algorithm
            for k, v in params:
                pstr += " -%s %s" % (k, v)
                algparam+= "-%s" % v
            odir = os.path.join(args.outdir, algparam)
            cmd = "java -cp %s de.lmu.ifi.dbs.elki.application.KDDCLIApplication -dbc.in %s -algorithm %s %s %s -evaluator AutomaticEvaluation -resulthandler ResultWriter -out %s" % (args.elki, args.infile, algorithm, OVERALLPARAMS, pstr, odir)
            cmds.append((algparam, odir, cmd))
    
    random.shuffle(cmds)
    idre = re.compile("^ID=([0-9]+) ")
    for algparam, odir, cmd in cmds:
        print >> sys.stderr, cmd
        os.system("time %s" % cmd)

        idx_to_cluster = {}
        # Now, read the clusters and visualize them against the tSNE points.
        for f in glob.glob("%s/cluster_*" % odir) + glob.glob("%s/noise.txt" % odir):
            if f == "%s/noise.txt" % odir:
                cluster = -1
            else:
                cluster = int(re.search("cluster_([0-9]+).txt", f).group(1))
            for l in open(f):
                if l[0] == "#": continue
                idx = int(idre.search(l).group(1))-1
                idx_to_cluster[idx] = cluster
        if len(idx_to_cluster) == 0: continue
        if len(idx_to_cluster) != len(points):
            print >> sys.stderr, "WARNING: len(idx_to_cluster) %d != len(points) %d" % (len(idx_to_cluster), len(points))
            continue
        labels = []
        for i in range(len(points)):
            labels.append(idx_to_cluster[i])
        assert len(labels) == len(points)
        render(labels, points, filename="%s/%s.png" % (odir, algparam))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Batch invoke ELKI on some datafile.')
    parser.add_argument('infile', help='in file (e.g. csv)')
    parser.add_argument('--outdir', default="out", help='out directory')
    parser.add_argument('--elki', default='elki.jar', help='ELKI jar file location')

    args = parser.parse_args()

    points = tsne(args)
    cluster(args, points)
