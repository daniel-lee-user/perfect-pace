import numpy as np
import racecourse
import matplotlib.pyplot as plt
import os.path
from abc import ABC, abstractmethod
import json
import argparse

# TODO: create export function for pacing plan
# TODO: ensure that paces sum up to target time

# GENERAL NOTE: for now, all units below are in feet for elevation and miles for distance (for readability). 
# later, we want to be able to work in any metric or imperial units.

class PacingPlan(ABC):
    def __init__(self,race_course : racecourse.RaceCourse, target_time, total_paces):
        self.target_time = target_time
        self.race_course = race_course
        self.current_m_paces = total_paces
        grades = self.race_course.grades
        adjustments = PacingPlan.get_pace_adjustments(grades)
        self.base_pace = (self.target_time - np.dot(adjustments, self.get_distances())) / np.sum(self.get_distances())
        self.optimal_paces = np.full(grades.shape, self.base_pace) + adjustments
        self.optimal_seg_times = np.multiply(self.get_distances(), self.optimal_paces)

        # Populated after pace recommendations are calculated
        self.critical_segments = np.ones(self.current_m_paces).astype(int)*-1
        self.true_paces_abbrev = np.ones(self.current_m_paces).astype(float) * -1 
        self.true_paces_full = np.ones(self.race_course.n_segments).astype(float) * -1
        self.elapsed_dists = np.ones(self.current_m_paces).astype(float) * -1
        self.true_seg_times = np.ones(self.current_m_paces).astype(float) * -1
        self.true_total_time = 0
    
    """Returns amount that we change the pace in minutes / mile for a given elevation grade using
    Jack Daniels formula"""
    @staticmethod
    def get_pace_adjustment_scalar(grade):
        if grade > 0:
            return (12 * abs(grade) / 60)
        else:
            return (-7 * abs(grade) / 60)

    @classmethod
    def get_pace_adjustments(cls, grades):
        vf = np.vectorize(cls.get_pace_adjustment_scalar)
        return vf(grades)
    
    def get_distances(self):
        return self.race_course.distances
    
    def get_n_segments(self):
        return self.race_course.n_segments  

    """Calculates pacing plan and populates relevant attributes"""
    @abstractmethod
    def calculate_recommendations(self):
        pass

    @staticmethod
    def get_pace_display_text(pace):
        m, s = divmod(pace*60, 60)
        return (f'{m:.0f}:{int(s):02d}')
    
    """Generates a .txt pacing plan that explicitly statements the pace run at every segment"""
    def gen_full_text(self):

        display_txt = ""
        for i in range(self.get_n_segments()):
            lat = self.race_course.lats[i]
            lon = self.race_course.lons[i]
            pace = self.true_paces_full[i]
            dist = self.race_course.distances[i]
            time = pace * dist
            elevation = self.race_course.elevations[i] # feet
        
            display_txt += f"{i}, {pace}, {lat}, {lon}, {elevation}, {dist}, {time} \n"
        return display_txt
    
    def gen_geojson(self, file_path, loop):
        # Initialize the base structure of the GeoJSON
        geojson_data = {
            "type": "FeatureCollection",
            "features": []
        }
        
        # Loop through each segment and create a new feature for each one
        all_changes = self.critical_segments
        if(all_changes[len(all_changes)-1] != self.get_n_segments()-1):
            all_changes = np.append(all_changes, self.get_n_segments()-1)
        start_idx = all_changes[0] # assuming changes always starts at 0
        for i in range(1, len(all_changes)):
            all_segments = []
            for j in range(start_idx, all_changes[i]+1):
                all_segments.append(self.race_course.segments[j])
            
            pace = self.true_paces_full[start_idx]
            
            coords = [[seg.start_lon, seg.start_lat, seg.start_ele] for seg in all_segments]
            if(i == len(all_changes)-1 and loop):
                # if last segment and loop is true
                first_seg = self.race_course.segments[0]
                coords.append([first_seg.start_lon, first_seg.start_lat, first_seg.start_ele])

            # Create a feature for each segment
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": coords
                },
                "properties": {
                    "pace": pace  # Add pace property
                }
            }
            
            # Append the feature to the features array in GeoJSON
            geojson_data["features"].append(feature)
            start_idx = all_changes[i]
        with open(file_path, 'w') as geojson_file:
            json.dump(geojson_data, geojson_file, indent=4)
        return geojson_data

    """Generates a simplified .txt pacing plan that includes just the different pace segments"""
    def gen_abbrev_plan(self):
        display_txt = ""

        header = f'{self.race_course.course_name}: {self.target_time} minute plan'
        display_txt += header + '\n\n'

        for i, pace in enumerate(self.true_paces_abbrev):
            lat_lon_txt = ''
            if self.race_course is type(racecourse.RealRaceCourse):
                lat_lon_txt = f' @ ({self.race_course.lats[i]},{self.race_course.lons[i]})'
            distance_duration = self.elapsed_dists[i]
            start_distance = self.race_course.start_distances[self.critical_segments[i]]
            txt = f"{i}: {start_distance:.2f} mi\t{self.get_pace_display_text(pace)}/mile for {distance_duration:.2f} mi{lat_lon_txt}"
            display_txt += txt + '\n'
        
        display_txt += f"\nTotal time: {self.true_total_time :.2f}"

        return display_txt
    
    def gen_pace_chart(self,file_path, incl_opt_paces=False, incl_true_paces=True):
        if not incl_opt_paces and not incl_true_paces:
            raise ValueError("at least one of incl_opt_paces or incl_true_paces must be True")

        fig,ax = plt.subplots()
        fig.set_figwidth(20)

        x = np.insert(self.race_course.end_distances, 0,0)
        y_elevations = np.append(self.race_course.elevations, self.race_course.end_elevations[-1])
        ax.plot(x, y_elevations, label ='elevation', color='blue')

        ax.set_xlabel('distance (miles)')
        ax.set_ylabel('elevation (feet)')
        ax.legend(loc="upper left")

        ax2 = ax.twinx()
        ax2.set_ylabel('pace (min/mile)')

        if incl_opt_paces:
            y_optimal_paces = np.append(self.optimal_paces, self.optimal_paces[-1])
            ax2.step(x, y_optimal_paces, label='optimal paces', color='orange', alpha=0.4, where='post')

        if incl_true_paces:
            y_true_paces = np.append(self.true_paces_full, self.true_paces_full[-1])
            ax2.step(x, y_true_paces, label='recommended paces', color='red', where='post')

            for i, xy in enumerate(zip(x, self.true_paces_full)):
                if i in self.critical_segments:
                    pace = self.true_paces_full[i]
                    ax2.annotate(f'{self.get_pace_display_text(pace)}', xy, xytext=(10,10), textcoords='offset pixels')

        ax.set_title(f'{self.race_course.course_name} Pacing Plan')
        plt.savefig(file_path, bbox_inches='tight',dpi=300)
    
    def __repr__(self, verbose=True):
        #TODO: only let this be called if pacing plan has been generated
        if verbose:
            return self.gen_full_text()
        else:
            return self.gen_abbrev_plan()
        
class PacingPlanBruteForce(PacingPlan):
    def __init__(self,race_course : racecourse.RaceCourse, target_time, total_paces):
        super().__init__(race_course, target_time, total_paces)
        n = self.get_n_segments()
        self.MIN_SEGMENT_LENGTH = 5 # TODO: test different values of this parameter; dynamically change its initialization based off the race course
        self.WP = np.zeros((n,n+1))
        self.LOSS = np.ones((n, n+1, total_paces)) * np.inf
        self.OPT = np.ones((n, n+1, total_paces)).astype(int)*-1
        self.cached_m_paces = 0

    """Returns the set of indices that represent the segments we change pace on for a pacing plan 
    for interval [i,k) with [a] pace changes remaining """
    def get_idxs(self,i,k,a, verbose=False):
        if verbose:
            print(f"range [{i},{k}) with {a} pace changes")
        if a == 0:
            return {i}
        j = self.OPT[i,k,a]
        if verbose:
            print(f"split on index {j}\n")
        right = self.get_idxs(j,k,a-1, verbose)
        right.add(i)
        return right
    
    def backtrack_solution(self):
        n = self.get_n_segments()
        m_paces = self.current_m_paces

        # list of segment indices where we change the paces
        self.critical_segments = np.array(sorted(self.get_idxs(0,n, self.current_m_paces-1))).astype(int)

        for j in range(m_paces):
            low = self.critical_segments[j]
            high = n if (j == m_paces - 1) else self.critical_segments[j+1]
            pace = self.WP[low, high]
            self.true_paces_full[low:high] = pace
            self.true_paces_abbrev[j] = pace

            # time calculations
            end_dist = self.race_course.end_distances[high-1]
            start_dist = self.race_course.start_distances[low]
            elapsed_dist = end_dist - start_dist
            self.elapsed_dists[j] = elapsed_dist
            self.true_seg_times[j] = pace * elapsed_dist
        
        self.true_total_time = np.sum(self.true_seg_times)

    def calculate_brute_force(self, verbose=True):
        n = self.get_n_segments()
        
        if self.cached_m_paces == 0:
            # TODO: rewrite using numpy vectorized functions
            for i in range(n):
                for j in range(i+1, n+1):
                    self.WP[i,j] = np.dot(self.optimal_paces[i:j], self.get_distances()[i:j] / sum(self.get_distances()[i:j]))
                    self.LOSS[i,j,0] = np.sum(self.optimal_paces[i:j] - self.WP[i,j])

        for a in range(max(1, self.cached_m_paces), self.current_m_paces):
            if verbose:
                print(f'PROGRESSED TO A = {a}')
            for i in range(n):
                # k >= i + number of pace changes + 1 
                for k in range(i+(a+1)*self.MIN_SEGMENT_LENGTH, n+1):
                    best_j = -1 
                    lowest_loss = np.inf
                    
                    for j in range(i+self.MIN_SEGMENT_LENGTH,k - self.MIN_SEGMENT_LENGTH + 1):
                        loss = self.LOSS[i,j,0] + self.LOSS[j,k,a-1]
                        if loss < lowest_loss:
                            lowest_loss = loss
                            best_j = j 
                    
                    self.LOSS[i,k,a] = lowest_loss
                    self.OPT[i,k,a] = int(best_j)
        
        self.cached_m_paces = self.current_m_paces

    def change_total_paces(self, new_m_paces):
        if new_m_paces > self.current_m_paces:
            self.LOSS = np.pad(self.LOSS, ((0,0), (0,0), (0,new_m_paces-self.current_m_paces)), 'constant', constant_values=np.inf)
            self.OPT = np.pad(self.OPT, ((0,0), (0,0), (0,new_m_paces-self.current_m_paces)), 'constant', constant_values=-1)
        
        self.critical_segments = np.ones(new_m_paces).astype(int)*-1
        self.true_paces_abbrev = np.ones(new_m_paces).astype(float) * -1 
        self.elapsed_dists = np.ones(new_m_paces).astype(float) * -1
        self.true_seg_times = np.ones(new_m_paces).astype(float) * -1

        self.current_m_paces = new_m_paces

    def calculate_recommendations(self, verbose=True):
        if self.current_m_paces > self.cached_m_paces:
            self.calculate_brute_force(verbose)
        self.backtrack_solution()
        self.full_seg_times = np.multiply(self.true_paces_full, self.race_course.distances)

def init_parser() -> argparse.ArgumentParser:
    '''
    Initializes the command line flag parser for this file.

    Flags:

    [REQUIRED]
    -f, --file  ==> file path
    -t, --time  ==> time in minutes to complete course
    -p, --paces ==> total number of paces

    [OPTIONAL]
    -l, --loop      ==> if the course contains a loop
    -s, --smoothen  ==> if the course should be smoothened
    -r              ==> if a randomly generated course should be used
    -h              ==> opens help menu
    '''
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", help="file path of the gpx file to be parsed", required=True)
    parser.add_argument("-t", "--time", type=int, help="time to complete course in minutes", required=True)
    parser.add_argument("-p", "--paces", type=int, help="the total number of paces", required=True)

    parser.add_argument("-l", "--loop", action="store_true", help="include this flag if the course contains a loop")
    parser.add_argument("-s", "--smoothen", action="store_true", help="include if the course should be smoothened (UNIMPLEMENTED)")
    parser.add_argument("-r", action="store_true", help="include this flag if you want a random course")

    return parser

def main():
    parser = init_parser()
    args = parser.parse_args()

    if args.r or args.smoothen:
        raise RuntimeError("unimplemented")

    file_path = args.file
    use_loop = args.loop
    use_smoothing = args.smoothen

    if len(file_path) == 0 or args.r:

        print("\nGenerating Random Course\n")
        n_segments = int(input('n_segments: \t\t\t'))
        distance = float(input('distance (miles): \t\t'))
        course_name = f'random {distance:.1f}'
        course = racecourse.RandomRaceCourse(course_name, n_segments, distance, use_smoothing=True)
        file_path = 'data/random/'

    else:
        course_name = os.path.basename(file_path).split('.')[0]
        course = racecourse.RealRaceCourse(course_name, file_path)

    print(f'\n{str(course)}')

    directory = os.path.dirname(file_path)+'/'+course_name +'/'
    if not os.path.exists(directory):
        os.makedirs(directory)

    plot_path = directory+f'{course_name} {course.n_segments} segs.jpg'

    try:
        course.gen_course_plot(plot_path)
    except Exception as e:
        print(plot_path)
        raise(e)
    
    print('\nCreating Pacing Plan\n')
    target_time = args.time
    current_m_paces = args.paces
    plan = PacingPlanBruteForce(course, target_time, current_m_paces)

    repeat = True
    is_first_iter = True

    while repeat:

        if not is_first_iter:
            new_m_paces = input("\nInput number of paces: ")
            plan.change_total_paces(int(new_m_paces))
            current_m_paces = new_m_paces
        
        plan_identifier = f'{target_time:.0f}min_{current_m_paces}p_{course.n_segments}'

        print('\nRunning Brute Force Algorithm\n')
        plan.calculate_recommendations(verbose=True)
        pace_plot_file_path = directory + plan_identifier + '.jpg'
        geojson_file_path   = directory + plan_identifier + '.json'
        pace_plan_file_path = directory + plan_identifier + '.txt'
        plan.gen_pace_chart(pace_plot_file_path, incl_opt_paces=True, incl_true_paces=True)
        plan.gen_geojson(geojson_file_path, use_loop)
        
        with open(pace_plan_file_path, 'w') as f:
            f.write(str(plan))

        repeat = bool(int(input('\nCreate another pace plan? 0/1\t')))
        is_first_iter = False
        
if __name__ == '__main__':
    main()
