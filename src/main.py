import argparse
import os
import race_course
from pacing_plan import PacingPlanBruteForce, PacingPlanLP

def init_parser() -> argparse.ArgumentParser:
    '''
    Initializes the command line flag parser for this file.

    Flags:

    [REQUIRED]
    -f, --file  ==> file path
    -t, --time  ==> time in minutes to complete course
    -p, --paces ==> total number of paces
    -m, --method    ==> pacing plan method to use ("brute_force", "linear_programming")

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
    parser.add_argument("-m", "--method", default="brute_force", choices=["brute_force", "linear_programming"],
                        help="pacing plan method to use. Options are 'brute_force' or 'linear_programming'", required=True)

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
        method = input("\nInput method (BF for Brute Force / LP for Linear Programming): ").strip().upper()
        if method in ["BF", "LP"]:
            break
        else:
            print("Invalid input. Please enter 'BF' for Brute Force or 'LP' for Linear Programming.")
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

    directory = os.path.join("results", course_name)
    if not os.path.exists(directory):
        os.makedirs(directory)

    plot_path = os.path.join(directory, f'{course_name} {course.n_segments} segs.jpg')

    try:
        course.gen_course_plot(plot_path)
    except Exception as e:
        print(plot_path)
        raise(e)
    if verbose:
        print('\nCreating Pacing Plan\n')
    target_time = args.time
    current_m_paces = args.paces
    if args.method == "brute_force":
        plan = PacingPlanBruteForce(course, target_time, current_m_paces)
        method = 'BF'
    elif args.method == "linear_programming":
        plan = PacingPlanLP(course, target_time, current_m_paces)
        method = 'LP'
    else:
        raise ValueError(f"Unknown pacing plan method: {args.method}")
    if verbose:
        print(f'\nCreating Pacing Plan using {args.method} method\n')

    repeat = args.repeat
    is_first_iter = True

    while repeat or is_first_iter:
        if not is_first_iter:
            old_method = method
            new_m_paces, method = get_new_inputs()
            plan.change_total_paces(new_m_paces)
            current_m_paces = new_m_paces
            if old_method != method:
                plan = PacingPlanBruteForce(course, target_time, current_m_paces) if method == 'BF' else PacingPlanLP(course, target_time, current_m_paces)
        
        plan_identifier = f'{target_time:.0f}min_{current_m_paces}p'
        if verbose:
            print('\nRunning Algorithm\n')
        plan.calculate_recommendations(verbose)
        pace_plot_file_path = os.path.join(directory, method + plan_identifier + '.jpg')
        geojson_file_path   = os.path.join(directory, method + plan_identifier + '.json')
        pace_plan_file_path = os.path.join(directory, method + plan_identifier + '.txt')
        plan.gen_pace_chart(pace_plot_file_path, incl_opt_paces=True, incl_true_paces=True)
        plan.gen_geojson(geojson_file_path, use_loop)
        
        with open(pace_plan_file_path, 'w') as f:
            f.write(str(plan))
        if repeat:
            repeat = bool(int(input('\nCreate another pace plan? 0/1\t')))
        is_first_iter = False
        
if __name__ == '__main__':
    main()
