from pacing_plan import *
from main import PACING_PLAN_METHODS
from pacing_plan_lp import PacingPlanLPAbsolute, PacingPlanLPSquare
from race_course import RealRaceCourse
from utils import Conversions
import os, shutil

from typing import Dict

PACING_PLAN_METHODS : Dict[str, PacingPlan]= {
    "BFA": PacingPlanBFAbsolute,
    "BFS": PacingPlanBFSquare,
    "LPA": PacingPlanLPAbsolute,
    "LPS": PacingPlanLPSquare,
    "APPM": PacingPlanAvgPacePerMile,
    "AP": PacingPlanAvgPace,
    "SEG": PacingPlanSegmenting
}


def main():
    methods = PACING_PLAN_METHODS
    course_names = ['boston',  'wineglass', 'FH-Fox', 'scurve', 'dodge']
    errors = ['beebe']
    total_paces = [1, 5, 10]
    # target_times = [100, ]
    courses : list[RealRaceCourse]= []

    base_directory = 'data/test-results/'

    for filename in os.listdir(base_directory):
        file_path = os.path.join(base_directory, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))

    for name in course_names:
        try:
            file_path = f'data/{name}.gpx'
            course = RealRaceCourse(name, file_path, N_SEGMENTS=200)
            courses.append(course)
        except:
            print(file_path)

    for course in courses:
        for name, value in methods.items():
            # try:
            total_paces = 1
            target_time = course.total_distance*6
            pacing_plan_class = value
            plan : PacingPlanStatic = pacing_plan_class(course, target_time, total_paces)
            
            course_directory = os.path.join(base_directory, course.course_name) 
            pacing_plan_directory = os.path.join(course_directory, name)
            if not os.path.exists(pacing_plan_directory):
                os.makedirs(pacing_plan_directory)
            print(course_directory, pacing_plan_directory)

            plan_identifier = f'{target_time:.0f}min_{total_paces}p'
            file_path = {
                'geojson': os.path.join(pacing_plan_directory, f'{plan_identifier}.json'),
                'plot': os.path.join(pacing_plan_directory, f'{plan_identifier}.jpg'),
                'plan_segments': os.path.join(pacing_plan_directory, f'{plan_identifier}_segments.json'),
                'plan_miles': os.path.join(pacing_plan_directory, f'{plan_identifier}_miles.json'),
                'plan_miles_txt': os.path.join(pacing_plan_directory, f'{plan_identifier}_miles.txt')
            }
            plan.calculate_recommendations( eps=1e-1)

            plan.gen_pace_chart(file_path['plot'], incl_opt_paces=True, incl_true_paces=True)
            plan.gen_geojson_full(file_path['geojson'], loop=False)
            
            plan.gen_text_plan(file_path["plan_miles"], export_mode = ExportMode.PER_MILE)
            plan.gen_geojson_per_mile(file_path["plan_miles"])
            plan.gen_geojson_abbrev(file_path['plan_segments'])

if __name__ == '__main__':
    main()