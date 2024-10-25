import numpy as np
import racecourse
import matplotlib.pyplot as plt
import sys 
import os.path
import json

conversion = {
    'meters_to_miles': 0.0006213712,
    'meters_to_feet': 3.28084,
    'miles_to_feet': 5280,
    'miles_to_meters': 1609.34,
    'feet_to_miles': 0.000189394,
    'feet_to_meters': 0.3048,
    'meters_to_km': 1000,
    'km_to_meters': 0.001
}

# TODO: create export function for pacing plan
# TODO: ensure that paces sum up to target time

# GENERAL NOTE: for now, all units below are in feet for elevation and miles for distance (for readability). 
# later, we want to be able to work in any metric or imperial units.

class PacingPlan:

    def __init__(self,race_course : racecourse.RaceCourse, target_time, max_paces):
        self.get_pace_adjustments_vf = np.vectorize(PacingPlan.get_pace_adjustment)
        self.target_time = target_time
        self.race_course = race_course
        self.max_paces = max_paces
        self.generate_optimal_paces()

    def get_grades(self):
        return self.race_course.grades
    
    def get_distances(self):
        return self.race_course.distances
    
    def get_n_segments(self):
        return self.race_course.n_segments
        
    def get_elapsed_time_of_plan(self, verbose=True):
        n = self.get_n_segments()
        times = []
        dists = []
        for i, pace in enumerate(self.recommended_paces):
            if i == len(self.recommended_paces) - 1:
                end_seg = n-1
            else:
                end_seg = self.changes[i+1] - 1
            end_dist = self.race_course.end_distance[end_seg]

            if i == 0:
                start_dist = 0
            else:
                start_seg = self.changes[i]
                start_dist = self.race_course.end_distance[start_seg-1]
            
            elapsed_dist = end_dist - start_dist
            
            time = pace*elapsed_dist
            if verbose == True:
                print(f'segment range [{self.changes[i]}, {end_seg+1}] has dist {elapsed_dist:.2f}')
                print(f'run at {pace:.2f} min / mile for {time:.2f} minutes')
            times += [time]
            dists += [elapsed_dist]

        self.elapsed_dists = dists
        self.segment_times = times

        self.true_time = sum(times)
        return self.true_time

    """Returns amount that we change the pace in minutes / mile for a given elevation grade using
    Jack Daniels formula"""
    @staticmethod
    def get_pace_adjustment(grade):
        if grade > 0:
            return (12 * abs(grade) / 60)
        else:
            return (-7 * abs(grade) / 60)
    
    def generate_optimal_paces(self):
        grades = self.get_grades()
        adjustments = self.get_pace_adjustments_vf(grades)
        self.base_pace = (self.target_time - np.dot(adjustments, self.get_distances())) / np.sum(self.get_distances())
        self.optimal_paces = np.full(grades.shape, self.base_pace) + adjustments
        self.segment_times = np.multiply(self.get_distances(), self.optimal_paces)

    @staticmethod
    def get_display_txt_for_pace(pace):
        # return (f'{pace:.2f}')
        m, s = divmod(pace*60, 60)
        return (f'{m:.0f}:{int(s):02d}')
    
    def gen_full_text(self):

        display_txt = ""
        for i in range(self.get_n_segments()):
            seg = self.race_course.segments[i]
            lat = seg.start_lat
            lon = seg.start_lon
            pace = self.agg_paces[i]
            elevation = seg.start_ele
        
            display_txt += f"{i}, {pace}, {lat}, {lon}, {elevation} \n"
        return display_txt
    
    def gen_geojson(self, file_path, loop):
        # Initialize the base structure of the GeoJSON
        geojson_data = {
            "type": "FeatureCollection",
            "features": []
        }
        
        # Loop through each segment and create a new feature for each one
        all_changes = self.changes
        if(all_changes[len(all_changes)-1] != self.get_n_segments()-1):
            all_changes = np.append(all_changes, self.get_n_segments()-1)
        start_idx = all_changes[0]# assuming changes always starts at 0
        for i in range(1, len(all_changes)):
            all_segments = []
            for j in range(start_idx, all_changes[i]+1):
                all_segments.append(self.race_course.segments[j])
            
            pace = self.agg_paces[start_idx]
            
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


    def gen_abbrev_plan(self):
        display_txt = ""

        header = f'{self.race_course.course_name}: {self.target_time} minute plan'
        display_txt += header + '\n\n'

        total_time = self.get_elapsed_time_of_plan(verbose=False)

        for i, pace in enumerate(self.recommended_paces):
            lat_lon_txt = ''
            if self.race_course is type(racecourse.RealRaceCourse):
                seg = self.race_course.segments[i]
                lat_lon_txt = f' @ ({seg.start_lat},{seg.start_lon})'
            distance_duration = self.elapsed_dists[i]
            start_distance = self.race_course.start_distance[self.changes[i]]
            txt = f"{i}: {start_distance:.2f} mi\t{self.get_display_txt_for_pace(pace)}/mile for {distance_duration:.2f} mi{lat_lon_txt}"
            display_txt += txt + '\n'
        
        display_txt += f"\nTotal time: {total_time:.2f}"

        return display_txt

    def __repr__(self, verbose=False):
        #TODO: only let this be called if pacing plan has been generated
        if verbose:
            return self.gen_full_text()
        else:
            return self.gen_abbrev_plan()
        

class PacingPlanDP(PacingPlan):
    def __init__(self,race_course : racecourse.RaceCourse, target_time, max_paces):
        super().__init__(race_course, target_time, max_paces)
        n = self.get_n_segments()
        self.WP = np.zeros((n,n+1))
        self.LOSS = np.ones((n, n+1, max_paces)) * np.inf
        self.OPT = np.ones((n, n+1, max_paces)).astype(int)*-1
    
    # TODO: optimize this using numpy functions
    # generates a complete array of paces that we run for every segment
    def gen_aggregate_paces(self):
        agg_paces = []
        for i in range(len(self.changes)):
            if i == self.max_paces - 1:
                high = self.get_n_segments()
            else:
                high = self.changes[i+1]
            num_copies = high - self.changes[i]
            to_add = [self.recommended_paces[i]]*num_copies
            agg_paces += to_add
        self.agg_paces = np.array(agg_paces)

    """Returns the set of indices that represent the segments we change pace on for a pacing plan 
    for interval [i,k) with [a] pace changes remaining """
    def get_idxs(self,i,k,a, verbose=True):
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
    
    def backtrack_solution(self, verbose=True):
        n = self.get_n_segments()

        # list of segment indices where we change the paces
        self.changes = np.array(sorted(self.get_idxs(0,n, self.max_paces-1, verbose))).astype(int)

        # TODO: Remove assertionerror
        if len(self.changes) != self.max_paces:
            raise AssertionError('Number of pace changes computed is not equal to max_paces')

        # list of pace changes (i.e. [5,7,6.5] means we run 5 min/mile at segment 0 )
        paces = []

        for j in range(self.max_paces-1):
            i1 = self.changes[j]
            i2 = self.changes[j+1]
            paces.append(self.WP[i1,i2])
        
        paces.append(self.WP[int(self.changes[-1]), n])

        self.recommended_paces = np.array(paces)

    def calculate_DP(self, verbose=True):
        n = self.get_n_segments()

        for i in range(n):
            for j in range(i+1, n+1):
                weighted_pace = np.dot(self.optimal_paces[i:j], self.get_distances()[i:j] / sum(self.get_distances()[i:j]))
                self.WP[i,j] = weighted_pace
                self.LOSS[i,j,0] = np.sum(np.square(self.optimal_paces[i:j] - weighted_pace))

        for a in range(1, self.max_paces):
            if verbose:
                print(f'PROGRESSED TO A = {a}')
            for i in range(n):
                # k >= i + number of pace changes + 1 
                for k in range(i+a+1, n+1):
                    j = i+1
                    best_j = j 
                    lowest_loss = self.LOSS[i,i+1,0] + self.LOSS[j,k,a-1]
                    
                    for j in range(i+1,k):
                        loss = self.LOSS[i,j,0] + self.LOSS[j,k,a-1]
                        if loss < lowest_loss:
                            lowest_loss = loss
                            best_j = j 
                    
                    self.LOSS[i,k,a] = lowest_loss
                    self.OPT[i,k,a] = int(best_j)

    def handle_DP(self, verbose):
        self.calculate_DP(verbose)
        self.backtrack_solution(verbose)
        self.gen_aggregate_paces()
        self.get_elapsed_time_of_plan() # generates elapsed time as well

    def gen_pace_chart(self,file_path, include_optimal_paces=False, include_recommended_paces=True):
        if not include_optimal_paces and not include_recommended_paces:
            raise ValueError("at least one of include_optimal_paces or include_recommended_paces must be True")

        fig,ax = plt.subplots()
        fig.set_figwidth(20)

        distances = np.insert(self.race_course.end_distance, 0,0)
        full_elevations = np.append(self.race_course.elevations, self.race_course.end_elevations[-1])
        ax.plot(distances, full_elevations, label ='elevation', color='blue')

        ax.set_xlabel('distance (miles)')
        ax.set_ylabel('elevation (feet)')
        ax.legend(loc="upper left")

        ax2 = ax.twinx()
        ax2.set_ylabel('pace (min/mile)')

        if include_optimal_paces:
            optimal_paces_y = np.append(self.optimal_paces, self.optimal_paces[-1])
            ax2.step(distances, optimal_paces_y, label='optimal paces', color='orange', alpha=0.4, where='post')

        if include_recommended_paces:
            agg_paces_y = np.append(self.agg_paces, self.agg_paces[-1])
            ax2.step(distances, agg_paces_y, label='recommended paces', color='red', where='post')

            for i, xy in enumerate(zip(distances, self.agg_paces)):
                if i in self.changes:
                    pace = self.agg_paces[i]
                    ax2.annotate(f'{self.get_display_txt_for_pace(pace)}', xy, xytext=(10,10), textcoords='offset pixels')

        ax.set_title(f'{self.race_course.course_name} Pacing Plan')
        plt.savefig(file_path, bbox_inches='tight',dpi=300)
    

def main():

    repeat = True
    while (repeat == True):

        file_path = str(input("\nfile path for .gpx file:\t"))
        
        use_loop = bool(input("\nIs the course a loop? 0/1\t"))

        if len(file_path) == 0:

            print("\nGenerating Random Course\n")
            n_segments = int(input('n_segments: \t\t\t'))
            distance = float(input('distance (miles): \t\t'))
            course_name = f'random {distance:.1f}'
            course = racecourse.RandomRaceCourse(course_name, n_segments, distance, use_smoothing=True)
            file_path = 'data/random/'

        else:
            course_name = os.path.basename(file_path).split('.')[0]
            use_smoothing = bool(input("\nUse Smoothing? 0/1\t\t"))
            course = racecourse.RealRaceCourse(course_name, file_path, use_smoothing)

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
        
        create_plan = bool(int(input('\ncreate pacing plan? 0/1\t\t')))

        if create_plan:
            print('\nCreating Pacing Plan\n')
            target_time = float(input('target time (minutes):\t\t'))
            max_paces = int(input('number of pace changes:\t\t'))
        else:
            sys.exit(1)

        plan = PacingPlanDP(course, target_time, max_paces)

        plan_identifier = f'{max_paces} paces {target_time:.0f} min {course.n_segments} segs'

        run_DP = bool(int(input('\nrun DP? 0/1\t\t\t')))

        if run_DP:
            print('\nRunning DP Algorithm\n')
            plan.handle_DP(verbose=True)
            pace_plot_file_path = directory+ plan_identifier + '.jpg'
            geojson_file_path   = directory+ plan_identifier + '.json'
            pace_plan_file_path = directory+ plan_identifier + '.txt'
            plan.gen_pace_chart(pace_plot_file_path, include_optimal_paces=True, include_recommended_paces=True)
            plan.gen_geojson(geojson_file_path, use_loop)
            
            with open(pace_plan_file_path, 'w') as f:
                f.write(str(plan))

        repeat = bool(int(input('\nCreate another pace plan? 0/1\t')))
        
if __name__ == '__main__':
    main()
