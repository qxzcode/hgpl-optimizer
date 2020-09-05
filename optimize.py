from argparse import ArgumentParser
import numpy as np
import matplotlib.pyplot as plt
import math
from sklearn.neighbors import KDTree
import itertools

from util import *


def path_length(path):
    return np.linalg.norm(path[1:] - path[:-1], axis=-1).sum()

def total_length(paths):
    return sum(path_length(path) for path in paths)


def make_up_paths(paths):
    new_paths = []
    for path1, path2 in zip(paths[:-1], paths[1:]):
        new_paths.append(np.array([path1[-1], path2[0]]))
    return new_paths


def summarize_paths(paths, plot=True):
    print(f'{len(paths)} paths')
    
    up_paths = make_up_paths(paths)
    down_dist = total_length(paths)
    up_dist = total_length(up_paths)
    print(f'pen down distance: {down_dist}')
    print(f'pen up distance:   {up_dist}')
    print(f'total distance:    {down_dist + up_dist}')
    
    if plot:
        for path, color in zip(paths, np.linspace(0, 1, len(paths))):
            red = min(color*2, 1.0)
            blue = min((1.0 - color)*2, 1.0)
            plt.plot(*path.T, c=[red, 0, blue])
        for path in up_paths:
            plt.plot(*path.T, c='black')
        plt.axis('equal')
        plt.get_current_fig_manager().full_screen_toggle()
        plt.show()


def main(args):
    starts = set()
    with open(args.infile) as f:
        content = f.read()
    
    paths = []
    try:
        for cmd in content.split(';'):
            cmd = cmd.strip()
            if len(cmd) == 0:
                continue
            if cmd.startswith('PU') or cmd.startswith('PD'):
                if cmd.startswith('PU'):
                    paths.append([])
                if len(cmd) > 2:
                    x, y = map(int, cmd[2:].split())
                    paths[-1].append((x, y))
    except:
        print(f'Error on line: {cmd}')
        raise
    if len(paths[-1]) == 0:
        paths.pop()
    paths = [np.array(path) for path in paths]
    
    summarize_paths(paths, plot=True)
    
    start_points = np.array([path[0] for path in paths])
    end_points = np.array([path[-1] for path in paths])
    
    loops = start_points == end_points
    loops = np.logical_and(loops[:, 0], loops[:, 1])
    print(f'{np.count_nonzero(loops)} / {loops.size} paths are loops')
    
    print('Optimizing...')
    with time_block('optimize paths'):
        cur_loc = [0, 0]
        remaining = set(range(len(paths)))
        path_mask = np.ones(len(paths), dtype=bool)
        path_indices = np.arange(len(paths))
        new_paths = []
        while len(remaining) > 0:
            with time_block('build KDTree', enable=False):
                tree = KDTree(start_points[path_mask])
            next_index = tree.query([cur_loc], k=1, return_distance=False)[0, -1]
            next_index = path_indices[path_mask][next_index]
            
            remaining.remove(next_index)
            path_mask[next_index] = False
            new_paths.append(paths[next_index])
            cur_loc = end_points[next_index]
    print('Done')
    
    summarize_paths(new_paths)
    
    with open(args.outfile, 'w') as f:
        f.write('IN;\n')
        f.write('SP1;\n')
        for path in new_paths:
            f.write('\n')
            f.write(f'PU{path[0][0]} {path[0][1]};\n')
            for pt in path[1:]:
                f.write(f'PD{pt[0]} {pt[1]};\n')
        f.write('\n')
        f.write('PU;\n')
        f.write('SP0;\n')
        f.write('IN;\n')


def parse_args():
    """Define, parse, and return the command-line arguments."""
    parser = ArgumentParser(description='Optimize HGPL plots')
    parser.add_argument('infile', help='the input file to optimize')
    parser.add_argument('outfile', help='the output file to write')
    
    return parser.parse_args()

if __name__ == '__main__':
    main(parse_args())
