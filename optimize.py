from argparse import ArgumentParser
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm

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
    total_dist = down_dist + up_dist
    print(f'pen down distance: {down_dist}')
    print(f'pen up distance:   {up_dist}')
    print(f'total distance:    {total_dist}')
    
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
    
    return total_dist


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
    
    print('=== BEFORE: ===')
    dist_before = summarize_paths(paths, plot=True)
    print()
    
    start_points = np.array([path[0] for path in paths])
    end_points = np.array([path[-1] for path in paths])
    
    with time_block('build candidate_points'):
        loops = start_points == end_points
        loops = np.logical_and(loops[:, 0], loops[:, 1])
        
        candidate_points = []
        candidate_path_indices = []
        candidate_point_indices = []  # -2=start, -1=end, 0-inf=[index in loop path]
        for i, (path, is_loop) in enumerate(zip(paths, loops)):
            if is_loop:
                candidate_points.append(path[:-1])
                candidate_path_indices.append(np.full(len(path)-1, i))
                candidate_point_indices.append(np.arange(len(path)-1))
            else:
                candidate_points.append([path[0], path[-1]])
                candidate_path_indices.append([i, i])
                candidate_point_indices.append([-2, -1])
        candidate_points = np.concatenate(candidate_points)
        candidate_path_indices = np.concatenate(candidate_path_indices)
        candidate_point_indices = np.concatenate(candidate_point_indices)
    
    print(f'{np.count_nonzero(loops)} / {loops.size} paths are loops')
    
    print('Optimizing...')
    OPT_SUB_TIMING = False
    
    # def get_nn_tree(points, query_loc):
    #     with time_block('build spatial index', enable=OPT_SUB_TIMING):
    #         tree = BallTree(points)
    #     with time_block('query spatial index', enable=OPT_SUB_TIMING):
    #         return tree.query([query_loc], k=1, return_distance=False)[0, -1]
    def get_nn_brute_force(points, query_loc):
        with time_block('compute squared distances', enable=OPT_SUB_TIMING):
            distances_sq = np.square(points - query_loc).sum(axis=-1)
        with time_block('get min', enable=OPT_SUB_TIMING):
            return distances_sq.argmin()
    
    with time_block('optimize paths'):
        cur_loc = [0, 0]
        remaining = set(range(len(paths)))
        path_mask = np.ones(len(candidate_points), dtype=bool)
        new_paths = []
        for _ in tqdm(range(len(paths)), unit='paths', disable=OPT_SUB_TIMING):
            with time_block('mask arrays', enable=OPT_SUB_TIMING):
                candidate_points_masked = candidate_points[path_mask]
                candidate_path_indices_masked = candidate_path_indices[path_mask]
                candidate_point_indices_masked = candidate_point_indices[path_mask]
            query_index = get_nn_brute_force(candidate_points_masked, cur_loc)
            path_index = candidate_path_indices_masked[query_index]
            meta = candidate_point_indices_masked[query_index]
            
            remaining.remove(path_index)
            with time_block('clear path_mask section', enable=OPT_SUB_TIMING):
                path_mask[candidate_path_indices == path_index] = False
            path = paths[path_index]
            if meta == -2:
                app_path = path
            elif meta == -1:
                app_path = path[::-1]
            else:
                with time_block('roll loop path', enable=OPT_SUB_TIMING):
                    app_path = np.roll(path[:-1], -meta, axis=0)
                    app_path = np.concatenate((app_path, app_path[:1]))  # close the loop
            new_paths.append(app_path)
            cur_loc = app_path[-1]
    
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
    print('Wrote output file')
    
    print()
    print('=== AFTER: ===')
    dist_after = summarize_paths(new_paths)
    print()
    
    dist_ratio = dist_after / dist_before
    print(f'Optimized is {100*dist_ratio:.1f}% of original total distance (~{1/dist_ratio:.1f}x as fast)')


def parse_args():
    """Define, parse, and return the command-line arguments."""
    parser = ArgumentParser(description='Optimize HGPL plots')
    parser.add_argument('infile', help='the input file to optimize')
    parser.add_argument('outfile', help='the output file to write')
    
    return parser.parse_args()

if __name__ == '__main__':
    main(parse_args())
