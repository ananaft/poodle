from config import *
from core import *

import ast
import re
import pymongo
import time


def check_question(json_string: str) -> dict:
    """
    Used by add_json() to check for correct question formatting.

    Dependencies: json
    """
    question_dict = json.loads(json_string)
    result_dict = {}

    # Function for missing question keys
    def check_missing(question: dict, keys: dict, output: dict) -> None:
        for k in keys.keys():
            if k not in question.keys():
                output[k] = 'Missing'
    # Function for data type check of keys
    def check_type(question: dict, keys: dict, output: dict) -> None:
        for k, v in keys.items():
            if k not in output.keys() and k in question.keys():
                if type(question[k]) != v:
                    output[k] = f'Wrong data type. Expected: {v}'

    # Functions for each moodle_type and general fields
    def check_general(question: dict) -> None:
        # Keys that are always present
        general_keys = {
            'name': str, 'question': str, 'family_type': str, 'points': int,
            'in_exams': dict, 'time_est': int, 'difficulty': int
        }
        check_missing(question, general_keys, result_dict)
        check_type(question, general_keys, result_dict)
        # Check for correct naming scheme
        if Q_CATEGORIES and 'name' not in result_dict:
            if question['name'][:-4] not in Q_CATEGORIES:
                result_dict['name'] = 'Wrong naming scheme'
        # Check for duplicate question name
        if QUESTIONS.find_one({'name': question['name']}):
            result_dict['name'] = 'Name already exists in database.'

        # Optional keys
        optional_keys = {
            'img_files': list, 'tables': dict
        }
        check_type(question, optional_keys, result_dict)

    def check_multichoice(question: dict) -> dict:
        check_general(question)

        multichoice_keys = {
            'correct_answers': list, 'false_answers': list
        }
        check_missing(question, multichoice_keys, result_dict)
        check_type(question, multichoice_keys, result_dict)
        # Check optional "single" key for value 0/1
        if 'single' in question.keys():
            if question['single'] not in range(0,2):
                result_dict['single'] = 'Expected value: 0/1'

        if result_dict:
            result_dict['__question_name__'] = question['name']

        return result_dict

    def check_numerical(question: dict) -> dict:
        check_general(question)

        numerical_keys = {
            'correct_answers': list
        }
        check_missing(question, numerical_keys, result_dict)
        check_type(question, numerical_keys, result_dict)
        # "tolerance" key can be int or float
        if 'tolerance' not in question.keys():
            result_dict['tolerance'] = 'Missing'
        else:
            if type(question['tolerance']) != int and type(question['tolerance']) != float:
                result_dict['tolerance'] = 'Wrong data type. Expected: int or float'

        if result_dict:
            result_dict['__question_name__'] = question['name']

        return result_dict

    def check_shortanswer(question: dict) -> dict:
        check_general(question)

        shortanswer_keys = {
            'correct_answers': list, 'usecase': int
        }
        check_missing(question, shortanswer_keys, result_dict)
        check_type(question, shortanswer_keys, result_dict)

        if result_dict:
            result_dict['__question_name__'] = question['name']

        return result_dict

    def check_essay(question: dict):
        check_general(question)

        essay_keys = {
            'answer_files': list
        }
        check_missing(question, essay_keys, result_dict)
        check_type(question, essay_keys, result_dict)

        if result_dict:
            result_dict['__question_name__'] = question['name']

        return result_dict
        
    def check_matching(question: dict):
        check_general(question)

        matching_keys = {
            'correct_answers': dict, 'false_answers': list
        }
        check_missing(question, matching_keys, result_dict)
        check_type(question, matching_keys, result_dict)

        if result_dict:
            result_dict['__question_name__'] = question['name']

        return result_dict
        
    def check_gapselect(question: dict):
        check_general(question)

        gapselect_keys = {
            'correct_answers': dict, 'false_answers': dict
        }
        check_missing(question, gapselect_keys, result_dict)
        check_type(question, gapselect_keys, result_dict)

        if result_dict:
            result_dict['__question_name__'] = question['name']

        return result_dict
        
    def check_ddimageortext(question: dict):
        check_general(question)

        ddimageortext_keys = {
            'correct_answers': list, 'drops': dict
        }
        check_missing(question, ddimageortext_keys, result_dict)
        check_type(question, ddimageortext_keys, result_dict)

        if result_dict:
            result_dict['__question_name__'] = question['name']

        return result_dict
        
    def check_calculated(question: dict):
        check_general(question)

        calculated_keys = {
            'correct_answers': list, 'tolerance': list, 'vars': list
        }
        check_missing(question, calculated_keys, result_dict)
        check_type(question, calculated_keys, result_dict)

        if result_dict:
            result_dict['__question_name__'] = question['name']

        return result_dict

    try:
        match question_dict['moodle_type']:
            case 'multichoice':
                result = check_multichoice(question_dict)
                return dict(sorted(result.items()))
            case 'numerical':
                result = check_numerical(question_dict)
                return dict(sorted(result.items()))
            case 'shortanswer':
                result = check_shortanswer(question_dict)
                return dict(sorted(result.items()))
            case 'essay':
                result = check_essay(question_dict)
                return dict(sorted(result.items()))
            case 'gapselect':
                result = check_gapselect(question_dict)
                return dict(sorted(result.items()))
            case 'ddimageortext':
                result = check_ddimageortext(question_dict)
                return dict(sorted(result.items()))
            case 'calculated':
                result = check_calculated(question_dict)
                return dict(sorted(result.items()))
            case _:
                return {'__question_name__': question_dict['name'], 'moodle_type': 'Unknown'}
    except KeyError:
        return {'__question_name__': question_dict['name'], 'moodle_type': 'Missing'}


def add_json(json_file: str) -> None:
    """
    Add questions to the database automatically by reading a JSON file.
    Questions need to be enclosed in list brackets.

    Dependencies: re, json
    """

    with open(json_file, 'r') as f:
        question_list = f.read()
        question_list = re.sub(r'\s', '', question_list)
        question_list = json.loads(question_list)

    error_list = []
    for q in question_list:
        check_result = check_question(json.dumps(q))
        if not check_result:
            QUESTIONS.insert_one(q)
        else:
            error_list.append(check_result)

    if not error_list:
        print('All questions added successfully!')
    else:
        print('Some questions could not be added due to errors:')
        pprint(error_list)


# def add_question():
#     """
#     This function's purpose is to add new questions to the database. It allows
#     for manual input of questions with auto-completion features targeted at
#     child questions.

#     ---------------------
#     Dependencies: config, core, re, pymongo
#     """

#     # Define sub-functions for each different moodle_type
#     def add_numerical(dictionary):
#         dictionary['correct_answers'] = []
#         dictionary['tolerance'] = 0.5

#     def add_multichoice(dictionary):
#         dictionary['correct_answers'] = []
#         dictionary['false_answers'] = []

#     def add_shortanswer(dictionary):
#         dictionary['correct_answers'] = []
#         dictionary['usecase'] = False

#     def add_essay(dictionary):
#         dictionary['answer_files'] = []

#     def add_matching(dictionary):
#         dictionary['correct_answers'] = {}
#         dictionary['false_answers'] = []

#     def add_gapselect(dictionary):
#         dictionary['correct_answers'] = {}
#         dictionary['false_answers'] = {}

#     def add_ddimageortext(dictionary):
#         dictionary['correct_answers'] = []
#         dictionary['drops'] = {}
#         dictionary['img_files'] = []

#     def add_coderunner(dictionary):
#         dictionary['correct_answers'] = []


#     if json != None:
#         if json[-5:] != '.json':
#             json = json + '.json'
#         # Open .json-file
#         with open(json, 'r') as rf:
#             question_file = rf.read()
#         # Create new string without newline characters
#         question_string = re.sub(r'\n', '', question_file)
#         # Creat dict based on string
#         try:
#             new_questions = ast.literal_eval(question_string)
#         except:
#             previous_line = [',\n', 0]
#             with open(json, 'r') as rf:
#                 for num, line in enumerate(rf, 1):
#                     # Integrity check for commas
#                     current_line = [line, num]
#                     if (previous_line[0][-2] not in [',', '[', ']', '{'] and
#                         not bool(re.match(r'\s*\},|\s*\],|\}\]', current_line[0]))
#                     ):
#                         print(f'Missing comma at line {previous_line[1]}.')
#                     previous_line = current_line
#                     # Integrity check for keys
#                     if bool(re.search(r'"\s{1}"', line)):
#                         print(f"Potentially missing ':' for key at line {num}.")
#         # Check for correct question naming scheme
#         if Q_CATEGORIES:
#             wrong_scheme = [
#                 q['name'] for q in new_questions if q['name'][:-4] not in Q_CATEGORIES
#             ]
#         else:
#             wrong_scheme = []
#         # Check for duplicates
#         collection_names = [q['name'] for q in QUESTIONS.find()]
#         duplicates = [
#             q['name'] for q in new_questions if q['name'] in collection_names
#         ]
#         if len(wrong_scheme) > 0 or len(duplicates):
#             print('Problematic questions found.\n' +
#                   f'Wrong naming scheme: {wrong_scheme}\n' +
#                   f'Duplicate question names: {duplicates}')
#             return 'Process aborted.'
#         result = QUESTIONS.insert_many([q for q in new_questions])
#     else:
#         family_type = fast_input(['parent', 'child', 'single'],
#                                  "Please specify question's family type." +
#                             "(Available types: 'parent', 'child', 'single')\n")
#         if family_type == 'child':
#             # Create dict of parent question
#             parent_name = input('Please specify the parent question: ')
#             if parent_name[-2:] != '00':
#                 parent_name = parent_name + '00'
#             parent_question = None
#             while parent_question == None:
#                 try:
#                     if QUESTIONS.find_one({'name': parent_name})['family_type'] == 'parent':
#                         parent_question = QUESTIONS.find_one({'name': parent_name})
#                     else:
#                         parent_name = input('Please specify a question with parent family type. ')
#                 except:
#                     parent_name = input('Question not in database! Please specify ' +
#                                         'a valid parent question. ')
#             parent_question['family_type'] = family_type
#             parent_question['in_exams'] = {}
#             # Look for placeholders in parent_question
#             for p in range(
#                     len(re.findall(r'\[\[.+?\]\]', parent_question['question']))
#             ):
#                 print(parent_question['question'])
#                 insertion = input(
#                     'Please input the text for placeholder %d: ' % (p+1)
#                 )
#                 parent_question['question'] = re.sub(
#                     r'\[\[.+?\]\]', insertion, parent_question['question'], count=1
#                 )
#             print(parent_question['question'])
#             # Go through question properties and potentially make changes
#             parent_question = inspect_properties(parent_question, mode = 'child')
#             # Drop _id-field of overwritten parent via dict comprehension
#             new_question = {
#                 i:parent_question[i] for i in parent_question if i != '_id'
#             }
#             # Adjust last two digits of question name
#             # --------------------------------------------
#             # Create search criterion based on parent name
#             q_name = re.compile(r'%s\d{2}' % (parent_name[:-2]))
#             # Look through collection
#             digits = [q['name'][-2:] for q in QUESTIONS.find({'name': q_name})]
#             digits.sort()
#             new_question['name'] = new_question['name'][:-2] + '%02d' % (int(digits[-1])+1)
#             result = QUESTIONS.insert_one(new_question)
#         else:
#             # Create general question template
#             new_question = {
#                 'name': '',
#                 'question': '',
#                 'family_type': family_type,
#                 'moodle_type': '',
#                 'points': 0,
#                 'in_exams': {},
#                 'time_est': 0,
#                 'difficulty': 0
#             }
#             # Ask for category
#             if Q_CATEGORIES:
#                 category = fast_input(Q_CATEGORIES,
#                                       "Please specify question's category.\n(Available " +
#                                       "categories: %s)\n" % (Q_CATEGORIES))
#             else:
#                 category = input("Please specify question's category: ")
#             # Determine new question's name
#             last_question = 0
#             for q in QUESTIONS.find({'name': re.compile(category)}):
#                 q_number = int(q['name'][-4:-2])
#                 if q_number > last_question:
#                     last_question = q_number
#             if family_type == 'parent':
#                 new_question['name'] = category + '%.2d' % (last_question+1) + '00'
#             else:
#                 new_question['name'] = category + '%.2d' % (last_question+1) + '99'
#             # Ask for moodle_type to determine needed sub-function
#             available_moodle_types = [
#                 'multichoice', 'numerical', 'essay', 'matching',
#                 'gapselect', 'shortanswer', 'coderunner', 'ddimageortext'
#             ]
#             moodle_type = fast_input(available_moodle_types,
#                                      "Please specify question's moodle_type.\n" +
#                                      "(Available types: %s)\n"  % (available_moodle_types))
#             new_question['moodle_type'] = moodle_type
#             # Execute needed sub-function to modify new_question
#             eval('add_' + moodle_type + '(new_question)')
#             # Ask if img_files field should be added
#             if moodle_type != 'ddimageortext':
#                 if yesno('Do you want to add an img_files field? (y/n)\n') == 'y':
#                     new_question['img_files'] = []
#             # Modify properties
#             new_question = inspect_properties(new_question, 'parsingle', inspect = False)
#             # Account for special multichoice cases
#             if (
#                     moodle_type == 'multichoice' and
#                     len(new_question['correct_answers']) == 1
#             ):
#                 prompt = ('Is this question supposed to allow checking of ' +
#                           'only one answer box? (y/n)\n')
#                 if yesno(prompt) == 'n':
#                     new_question['single'] = False
#             # Add question to collection
#             result = QUESTIONS.insert_one(new_question)
#     # Summary
#     if type(result) == pymongo.results.InsertManyResult:
#         added_list = [
#             QUESTIONS.find_one({'_id': i})['name'] for i in result.inserted_ids
#         ]
#         print('Questions ' + ("'{}', " * len(added_list))[:-2].format(
#             *added_list
#         ) + ' succesfully added.')
#     else:
#         print('Question {} successfully added.'.format(
#             QUESTIONS.find_one({'_id': result.inserted_id})['name']
#         ))


def edit_question(question, edits={}, history=False):
    """
    This function allows for fast editing of questions, slimming down the bulky
    syntax of pymongo.

    Arguments:
    ----------
    question (str):
      Name of the question you want to edit.
    edits (dict):
      Changes to be made in form of a dictionary where key is field name and
      value is field content. Fields can be edited manually if left empty.
    history (bool):
      If set to True, will add or modify the history field which contains a
      documentation of the changes.

    ------------------
    Dependencies: config, core, time
    """

    if edits:
        if history:
            # Get old or create new history field
            try:
                history_dict = QUESTIONS.find_one({'name': question})['history']
            except:
                history_dict = {}
            for k,v in edits.items():
                try:
                    # Save old contents for documentation
                    old_key = str(k) + '_old'
                    old_value = QUESTIONS.find_one({'name': question})[k]
                except:
                    pass
                new_key = str(k) + '_new'
                new_value = v
                # Overwrite history field
                try:
                    history_dict[
                        time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
                    ] = {old_key: old_value, new_key: new_value}
                except:
                    history_dict[
                        time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
                    ] = {new_key: new_value}
                QUESTIONS.find_one_and_update(
                    {'name': question}, {'$set': {'history': history_dict}}
                )
                QUESTIONS.find_one_and_update(
                    {'name': question}, {'$set': {k: v}}
                )
        else:
            for k,v in edits.items():
                QUESTIONS.find_one_and_update(
                    {'name': question}, {'$set': {k: v}}
                )
    # Manual editing
    else:
        if history:
            # Get old or create new history field
            try:
                history_dict = QUESTIONS.find_one({'name': question})['history']
            except:
                history_dict = {}
        q_dict = QUESTIONS.find_one({'name': question})
        print("Enter 'quit' at the following prompt to quit editing.")
        field = input('Edit field: ')
        while field.lower() != 'quit':
            if field not in q_dict.keys():
                print('Please input a valid field key.')
            else:
                q_dict = inspect_properties(q_dict, mode=field)
                if history:
                    try:
                        # Save old contents for documentation
                        old_key = field + '_old'
                        old_value = QUESTIONS.find_one({'name': question})[field]
                    except:
                        pass
                    new_key = field + '_new'
                    new_value = q_dict[field]
                    # Overwrite history field
                    try:
                        history_dict[
                            time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
                        ] = {old_key: old_value, new_key: new_value}
                    except:
                        history_dict[
                            time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
                        ] = {new_key: new_value}
                    QUESTIONS.find_one_and_update(
                    {'name': question}, {'$set': {'history': history_dict}}
                    )
                QUESTIONS.find_one_and_update(
                    {'name': question}, {'$set': {field: q_dict[field]}}
                )
            field = input('Edit field: ')


def remove_question(question, archive=False):
    """
    Simple function for question deletion.

    Arguments:
    ----------
    question (str):
      Name of the question that will be removed from the database.
    archive (bool):
      If set to True, a copy of the question will be moved to the archive
      collection.

    --------------------
    Dependencies: config
    """

    if archive == False:
        result = QUESTIONS.delete_one({'name': question})
    else:
        q = QUESTIONS.find_one({'name': question})
        q.pop('_id')
        DB.archive.insert_one(q)
        result = QUESTIONS.delete_one({'name': question})
    if result.deleted_count:
        print('Question successfully removed.')
    else:
        print(f"Question '{question}' not in collection. Nothing to remove.")
