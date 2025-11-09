import os
import json
import math
import re
from typing import Any, Dict, Mapping, Optional
import pandas as pd

def generate_data_visualization(
        config, 
        selected_scorecard_courses, 
        selected_scorecard_instructors,
        csv_path
):
    print ("  🏫 Generating Course Data Visualizations")
    for index, course in selected_scorecard_courses.iterrows():
        generate_course_grade_histogram(config, course, csv_path)
        generate_course_history_graph(config, course, csv_path)
    
    print ("  👨‍🏫 Generating Instructor Data Visualizations")
    for index, instructor in selected_scorecard_instructors.iterrows():
        generate_instructor_course_gpa_graph(config, instructor, csv_path)

def generate_course_grade_histogram(
        config, 
        course: Mapping[str, Any],
        csv_path
):
    
    subject = str(course.get("Subject", "")).strip()
    catalog = str(course.get("Catalog Nbr", "")).strip()
    term = str(course.get("Term", "")).strip()
    year = str(course.get("Year", "")).strip()
    instructor = str(course.get("Instructor", "")).strip()

    print(f"    🟧 Placeholder - Generate grade histogram for {subject} {catalog}, {term} {year} ({instructor})") 
    
    #TODO

def generate_course_history_graph(
        config, 
        course: Mapping[str, Any],
        csv_path
):
    
    subject = str(course.get("Subject", "")).strip()
    catalog = str(course.get("Catalog Nbr", "")).strip()
    term = str(course.get("Term", "")).strip()
    year = str(course.get("Year", "")).strip()
    instructor = str(course.get("Instructor", "")).strip()

    print(f"    🟧 Placeholder - Generate course history graph for {subject} {catalog}, {term} {year} ({instructor})") 
    
    #TODO

def generate_instructor_course_gpa_graph(
        config, 
        instructor: Mapping[str, Any],
        csv_path
):
    
    name = str(instructor.get("Instructor", "")).strip()

    print(f"    🟧 Placeholder - Generate instructor course GPA graph for {name}") 
    
    #TODO