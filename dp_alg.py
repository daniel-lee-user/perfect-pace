import numpy as np
import racecourse
import matplotlib
import matplotlib.pyplot as plt
import sys 
import os.path

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
        self.adjust_pace_vf = np.vectorize(PacingPlan.adjust_pace)
        self.target_time = target_time
        self.race_course = race_course
        self.max_paces = max_paces
        self.base_pace = target_time / self.get_total_distance() #average ideal pace for target time
        preadjusted_paces = self.adjust_pace_vf(self.base_pace, self.get_grades())
        preadjusted_times = np.multiply(self.get_distances(), preadjusted_paces)

        self.optimal_paces, self.segment_times = self.adjust_paces_to_fit_target_time(preadjusted_paces, preadjusted_times)    

    def get_grades(self):
        return self.race_course.grades
    
    def get_total_distance(self):
        return self.race_course.total_distance
    
    def get_distances(self):
        return self.race_course.distances
    
    def get_n_segments(self):
        return self.race_course.n_segments
    
    def get_optimal_pace_for_segment(self, idx):
        return self.optimal_paces[idx]
        
    def get_elapsed_time_of_plan(self, verbose=True):
        n = self.get_n_segments()
        times = []
        for i, pace in enumerate(self.recommended_paces):
            if i == len(self.recommended_paces) - 1:
                end_seg = n-1
            else:
                end_seg = self.changes[i+1] - 1
            end_dist = self.race_course.agg_distance[end_seg]

            if i == 0:
                start_dist = 0
            else:
                start_seg = self.changes[i]
                start_dist = self.race_course.agg_distance[start_seg-1]
            
            elapsed_dist = end_dist - start_dist
            
            time = pace*elapsed_dist
            if verbose == True:
                print(f'segment range [{self.changes[i]}, {end_seg+1}] has dist {elapsed_dist:.2f}')
                print(f'run at {pace:.2f} min / mile for {time:.2f} minutes')
            times += [time]

        self.segment_times = times
        return sum(times)

    """Returns optimal pace in minutes / mile for a given elevation grade using
    Jack Daniels formula"""
    @staticmethod
    def adjust_pace(base_pace, grade):
        if grade > 0:
            # Uphill
            return base_pace + (12 * abs(grade) / 60) 
        else:
            # Downhill
            return base_pace - (7 * abs(grade) / 60)
        
    """TODO: rewrite to modify paces directly rather than returning """
    def adjust_paces_to_fit_target_time(self, paces, segment_times):
        adjustment_factor = self.target_time / segment_times.sum()
        paces = paces*adjustment_factor
        segment_times = np.multiply(self.get_distances(), paces)
        return paces, segment_times

    """Generates optimal paces at each segment and writes to instance"""
    def generate_optimal_paces(self, target_time):
        self.target_time = target_time
        self.base_pace = target_time / self.total_distance #average ideal pace for target time
        preadjusted_paces = self.adjust_pace_vf(self.base_pace, self.grades)
        preadjusted_times = np.multiply(self.get_distances(), preadjusted_paces)

        self.optimal_paces, self.segment_times = self.adjust_paces_to_fit_target_time(preadjusted_paces, preadjusted_times)    

class PacingPlanDP(PacingPlan):
    def __init__(self,race_course : racecourse.RaceCourse, target_time, max_paces):
        super().__init__(race_course, target_time, max_paces)
        n = self.get_n_segments()
        self.WP = np.zeros((n,n+1))
        self.LOSS = np.ones((n, n+1, max_paces)) * np.inf #TODO: change to infinity, or empty?
        self.OPT = np.ones((n, n+1, max_paces)).astype(int)*-1
    
    # TODO: Optional function, returns the pace you run at segment i
    def get_pace_for_idx(self, i):
        raise NotImplementedError("get_pace_for_idx is not implemented")
    
    # TODO: Optional function, return pace you run at the [dist] point in the race. 
    def get_pace_for_dist(self, dist):
        raise NotImplementedError("")

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
        if j == 49:
            print(f"FOUND 49 range [{i},{k}) with {a} pace changes")
        if verbose:
            print(f"split on index {j}\n")
        right = self.get_idxs(j,k,a-1)
        right.add(i)

        if -1 in right:
            print(f'negative idx returned for range [{i},{k}) with {a} pace changes')
        return right
    
    def backtrack_solution(self, verbose=True):
        n = self.get_n_segments()

        # list of segment indices where we change the paces
        self.changes = np.array(sorted(self.get_idxs(0,n, self.max_paces-1)))

        # Todo: Remove assertionerror
        if len(self.changes) != self.max_paces:
            raise AssertionError('Number of pace changes computed is not equal to max_paces')

        # list of pace changes (i.e. [5,7,6.5] means we run 5 min/mile at segment 0 )
        paces = []

        # TODO: debug so that we don't have to reference self.changes and instead can use max_paces
        for j in range(self.max_paces-1):
            i1 = int(self.changes[j])
            i2 = int(self.changes[j+1]) # TODO: troubleshoot so this does not manually need to be cast to an int
            paces.append(self.WP[i1,i2])
        
        paces.append(self.WP[int(self.changes[-1]), n])

        self.recommended_paces = np.array(paces)

    def calculate_DP(self, verbose=True):
        n = self.get_n_segments()
        # OPT[i,j,k]: contains the value that we split on with k paces. 
        for i in range(n):
            for j in range(i+1, n+1):
                weighted_pace = np.dot(self.optimal_paces[i:j], self.get_distances()[i:j] / sum(self.get_distances()[i:j]))
                self.WP[i,j] = weighted_pace
                self.LOSS[i,j,0] = np.sum(np.square(self.optimal_paces[i:j] - weighted_pace))
                self.OPT[i,j,0] = -1 

        for a in range(1, self.max_paces):
            if verbose:
                print(f'PROGRESSED TO A = {a}')
            for i in range(n):
                # k >= i + number of pace changes + 1 
                # j represents the value we split the interval [i,k] on to search the subproblem
                for k in range(i+a+1, n+1):
                    
                    j = i+1
                    best_j = j 
                    lowest_loss = self.LOSS[i,i+1,0] + self.LOSS[j,k,a-1]
                    
                    for j in range(i+1,k):
                        loss = self.LOSS[i,j,0] + self.LOSS[j,k,a-1]
                        if loss < lowest_loss:
                            lowest_loss = loss
                            best_j = j 
                    
                    # TODO: Remove this when debugging is complete
                    if verbose and self.LOSS[i,k,a-1] == lowest_loss:
                        print(f'DON\'T NEED TO SPLIT on interval [{i}:{k}] and a = {a}')
                    
                    self.LOSS[i,k,a] = lowest_loss
                    self.OPT[i,k,a] = int(best_j)

    def handle_DP(self, verbose):
        self.calculate_DP(verbose)
        self.backtrack_solution(verbose)
        self.gen_aggregate_paces()

    def gen_pace_chart(self,file_path, include_optimal_paces=False, include_recommended_paces=True):
        if not include_optimal_paces and not include_recommended_paces:
            raise ValueError("at least one of include_optimal_paces or include_recommended_paces must be True")

        fig,ax = plt.subplots()
        fig.set_figwidth(20)
        distance_starts = np.insert(self.race_course.agg_distance, 0,0)[:-1]
        ax.plot(distance_starts, self.race_course.elevations, label ='elevation', color='blue')
        ax.set_xlabel('distance (miles)')
        ax.set_ylabel('elevation (feet)')
        ax.legend(loc="upper left")

        ax2 = ax.twinx()

        if include_optimal_paces:
            ax2.step(distance_starts, self.optimal_paces, label='optimal paces', color='orange', alpha=0.4)

        if include_recommended_paces:
            ax2.step(distance_starts, self.agg_paces, label='recommended paces', color='red')

            for i, xy in enumerate(zip(distance_starts, self.agg_paces)):
                if i in self.changes:
                    ax2.annotate(f'{self.agg_paces[i]:.2f}', xy)

        ax.set_title(f'{self.race_course.course_name} Pacing Plan')
        plt.savefig(file_path, bbox_inches='tight',dpi=300)

    def __repr__(self):
        display_txt = ""

        for i, pace in enumerate(self.recommended_paces):
            txt = f"{self.changes[i]}: " + f"{pace:.2f} min / mile"
            display_txt += txt + '\n'
        
        display_txt += f"\nTotal time: {self.get_elapsed_time_of_plan(verbose=False):.2f}"

        return display_txt
    

def main():

    repeat = True
    while (repeat == True):

        file_path = str(input("\nfile path for .gpx file:\t"))
        # file_path = "data/" + str(input("\nfile name for .gpx file:\t"))

        if len(file_path) == 0:

            print("\nGenerating Random Course\n")
            n_segments = int(input('n_segments: \t\t\t'))
            distance = float(input('distance (miles): \t\t'))
            course_name = f'random_{distance:.2f}'
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

        plot_path = directory+'plot_path.jpg'

        try:
            course.gen_race_plot(plot_path)
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

        plan_identifier = f'{max_paces}_{target_time:.1f}'

        run_DP = bool(int(input('\nrun DP? 0/1\t\t\t')))

        if run_DP:
            print('\nRunning DP Algorithm\n')
            plan.handle_DP(verbose=True)
            pace_plot_file_path = directory+'pace_plan_' + plan_identifier + '.jpg'
            pace_plan_file_path = directory+'pace_plan_' + plan_identifier + '.txt'
            plan.gen_pace_chart(pace_plot_file_path, include_optimal_paces=True, include_recommended_paces=True)
            
            with open(pace_plan_file_path, 'w') as f:
                f.write(str(plan))

        repeat = bool(int(input('\nCreate another pace plan? 0/1\t')))
if __name__ == '__main__':
    main()
