import argparse
import os
import race_course
from pacing_plan import PacingPlanBFAbsolute, PacingPlanBFSquare, PacingPlanAvgPacePerMile, PacingPlanAvgPace, PacingPlanSegmenting
from pacing_plan_lp import PacingPlanLPAbsolute, PacingPlanLPSquare

PACING_PLAN_METHODS = {
    "BFA": PacingPlanBFAbsolute,
    "BFS": PacingPlanBFSquare,
    "LPA": PacingPlanLPAbsolute,
    "LPS": PacingPlanLPSquare,
    "APPM": PacingPlanAvgPacePerMile,
    "AP": PacingPlanAvgPace,
    "SEG": PacingPlanSegmenting
}

def init_parser() -> argparse.ArgumentParser:
    '''
    Initializes the command line flag parser for this file.

    Flags:

    [REQUIRED]
    -f, --file  ==> file path
    -t, --time  ==> time in minutes to complete course
    -p, --paces ==> total number of paces
    -m, --method    ==> pacing plan method to use

    [OPTIONAL]
    -l, --loop      ==> if the course contains a loop
    -s, --smoothen  ==> if the course should be smoothened
    --random        ==> if a randomly generated course should be used
    -v, --verbose   ==> if the pacing plan should be generated in verbose mode
    -r, --repeat    ==> if the user wants to repeat generating pacing plans
    -h              ==> opens help menu
    '''
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", help="file path of the gpx file to be parsed", required=True)
    parser.add_argument("-t", "--time", type=int, help="time to complete course in minutes", required=True)
    parser.add_argument("-p", "--paces", type=int, help="the total number of paces", required=True)
    parser.add_argument("-m", "--method", default="BF", choices=PACING_PLAN_METHODS.keys(),
                        help="pacing plan method to use. Options are: " + ", ".join(PACING_PLAN_METHODS.keys()), required=True)

    parser.add_argument("-l", "--loop", action="store_true", help="include this flag if the course contains a loop")
    parser.add_argument("-s", "--smoothen", help="include if the course should be smoothened. running_avg, loess")
    parser.add_argument("--random", action="store_true", help="include this flag if you want a random course")
    parser.add_argument("-v", "--verbose", action="store_true", help="Include this flag if you would like to generate the pacing plan in verbose mode")
    parser.add_argument("-r", "--repeat", action="store_true", help="If you would like to repeat generating pacing plans")

    return parser

def get_new_inputs():
    while True:
        try:
            new_m_paces = int(input("\nInput number of paces (must be a positive integer): "))
            if new_m_paces > 0:
                break
            else:
                print("Please enter a positive integer for the number of paces.")
        except ValueError:
            print("Invalid input. Please enter a positive integer.")

    while True:
        method = input(f"\nInput method (must be a valid method): ").strip().upper()
        if method in PACING_PLAN_METHODS:
            break
        else:
            print("Invalid input. Available methods: " + ", ".join(PACING_PLAN_METHODS.keys()))
    return new_m_paces, method

def main():
    parser = init_parser()
    args = parser.parse_args()

    if args.random:
        raise RuntimeError("unimplemented")

    file_path = args.file
    use_loop = args.loop
    verbose = args.verbose

    if len(file_path) == 0 or args.random:

        if verbose:
            print("\nGenerating Random Course\n")
        n_segments = int(input('n_segments: \t\t\t'))
        distance = float(input('distance (miles): \t\t'))
        course_name = f'random {distance:.1f}'
        course = race_course.RandomRaceCourse(course_name, n_segments, distance)
        file_path = 'results/random/'

    else:
        course_name = os.path.basename(file_path).split('.')[0]
        course = race_course.RealRaceCourse(course_name, file_path)

    if args.smoothen:
        course.smoothen_segments(args.smoothen)

    if verbose:
        print(f'\n{str(course)}')

    course_directory = os.path.dirname(file_path)+'/results/'+course_name +'/'
    if not os.path.exists(course_directory):
        os.makedirs(course_directory)

    plot_path = os.path.join(course_directory, f'{course_name} {course.n_segments} segs.jpg')

    try:
        course.gen_course_plot(plot_path)
    except Exception as e:
        print(plot_path)
        raise(e)

    if verbose:
        print('\nCreating Pacing Plan\n')

    target_time = args.time
    current_m_paces = args.paces
    method = args.method
    pacing_plan_class = PACING_PLAN_METHODS[method]
    plan = pacing_plan_class(course, target_time, current_m_paces)

    pacing_plan_directory = os.path.join(course_directory, method)
    if not os.path.exists(pacing_plan_directory):
        os.makedirs(pacing_plan_directory)

    repeat = args.repeat
    is_first_iter = True

    while repeat or is_first_iter:
        if not is_first_iter:
            old_method = method
            new_m_paces, method = get_new_inputs()
            pacing_plan_class = PACING_PLAN_METHODS[method]
            plan.change_total_paces(new_m_paces)
            current_m_paces = new_m_paces
            if old_method != method:
                # Re-initialize the plan if the method has changed
                plan = pacing_plan_class(course, target_time, current_m_paces)

        plan_identifier = f'{target_time:.0f}min_{current_m_paces}p'
        
        if verbose:
            print(f'\nRunning Algorithm: {method}\n')
        
        plan.calculate_recommendations(verbose)

        file_path = {
            'geojson': os.path.join(pacing_plan_directory, f'{plan_identifier}.json'),
            'plot': os.path.join(pacing_plan_directory, f'{plan_identifier}.jpg'),
            'plan_segments': os.path.join(pacing_plan_directory, f'{plan_identifier}_segments.json'),
            'plan_miles': os.path.join(pacing_plan_directory, f'{plan_identifier}_miles.json')
        }

        plan.gen_geojson(file_path['geojson'], use_loop)
        plan.gen_pace_chart(file_path['plot'], incl_opt_paces=True, incl_true_paces=True)
        #plan.gen_plan_per_mile(file_path["plan_miles"], use_csv=False)
        plan.gen_plan_per_mile_json(file_path["plan_miles"])
        plan.gen_abbrev_plan_json(file_path['plan_segments'])
        #with open(file_path['plan_segments'], 'w') as f:
        #    f.write(plan.gen_abbrev_plan())

        if repeat:
            repeat = bool(int(input('\nCreate another pace plan? 0/1\t')))
        is_first_iter = False

if __name__ == '__main__':
    main()
