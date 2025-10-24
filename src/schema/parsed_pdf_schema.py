import json

PART_1_LIMITS = {"start": 1, "end": 7}
PART_2_LIMITS = {"start": 8, "end": 16}
OVERALL_EVAL_LIMITS = {'start': 17, 'end': 18}
GENERAL_INFO_LIMITS = {"start": 19, "end": 22}

def initialize_pdf_json():
    return{
        "eval_info":{
            "department" : None,
            "course" : None,
            "professor" : None,
            "year" : None,
            "term" : None,
            "response_count" : None,
            "total_students" : None,
            "response_rate": None,
            "avg1" : None,
            "avg2" : None,
        },
        "part_1":{
            "textbook_avg": None,
            "homework_value_avg": None,
            "lab_value_avg": None,
            "exam_reason_avg": None,
            "lab_weight_avg": None,
            "homework_weight_avg": None,
            "grade_crit_avg": None,
        },
        "part_2":{
            "instr_prep_avg": None,
            "instr_comm_idea_avg": None,
            "availability_avg": None,
            "enthus_avg": None,
            "instr_approach_avg": None,
            "course_mat_application_avg": None,
            "present_methods_avg": None,
            "fair_grading_avg": None,
            "timely_grading_avg": None,
        },
        "overall_eval":{
            "overall_quality_avg": None,
            "student_rating_avg": None,
        },
        "general_info":{
            "req_course_avg":{
                "yes": [None, None],
                "no": [None, None],
            },
            "hrs_per_wk_avg":{
                "16hr": [None, None],
                "8hr": [None, None],
                "4hr": [None, None],
                "2hr": [None, None],
                "1hr": [None, None],
            },
            "class_standing_avg":{
                "freshman": [None, None],
                "sophomore": [None, None],
                "junior": [None, None],
                "senior": [None, None],
                "grad": [None, None],
            },
            "attended_avg": {
                "90_to_100": [None, None],
                "70_to_89": [None, None],
                "50_to_69": [None, None],
                "30_to_49": [None, None],
                "10_to_29": [None, None],
            },
        },
        "free_response": {"liked": [], "disliked": [], "comments": []}}
def get_key_map():
    key_map = {}
    part_1_keys = [
            "textbook_avg", "homework_value_avg", "lab_value_avg",
            "exam_reason_avg", "lab_weight_avg", "homework_weight_avg",
            "grade_crit_avg",
    ]
    for quest_num, key in enumerate(part_1_keys, PART_1_LIMITS['start']):
        key_map[quest_num] = ("part_1", key)

    part_2_keys = [
            "instr_prep_avg", "instr_comm_idea_avg", "availability_avg",
            "enthus_avg", "instr_approach_avg", "course_mat_application_avg",
            "present_methods_avg", "fair_grading_avg", "timely_grading_avg",
    ]
    for quest_num, key in enumerate(part_2_keys, (PART_2_LIMITS['start'])):
        key_map[quest_num] = ("part_2", key)
        
    overall_eval_keys = [
            "overall_quality_avg", "student_rating_avg",
    ]
    for quest_num, key in enumerate(overall_eval_keys, (OVERALL_EVAL_LIMITS['start'])):
        key_map[quest_num] = ("overall_eval", key)

    # TODO: Update key mapping for general info questions
    general_info_keys = [
            "req_course_avg", "hrs_per_wk_avg", "class_standing_avg",
            "attended_avg",
    ]
    for quest_num, key in enumerate(general_info_keys, (GENERAL_INFO_LIMITS['start'])):
        key_map[quest_num] = ("general_info", key)
    
    # TODO: Update key mapping for free response questions
    """
    free_reponse = [
            "req_course_avg", "hrs_per_wk_avg", "class_standing_avg",
            "attended_avg",
    ]
    for quest_num, key in enumerate(general_info_keys, (GENERAL_INFO_LIMITS['start'])):
        key_map[quest_num] = ("general_info", key)"""

    return key_map