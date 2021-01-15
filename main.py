from selenium import webdriver
import usersettings
import time
import math
import json

driver = webdriver.Chrome()

driver.get("https://powerschool.vcs.net/public/home.html")

username_field = driver.find_element_by_name("account")
password_field = driver.find_element_by_name("pw")
submit_btn = driver.find_element_by_id("btn-enter-sign-in")

username_field.send_keys(usersettings.name)
password_field.send_keys(usersettings.pw)
submit_btn.click()


#--------------------------------------------------------------------------------


class Category:
    def __init__(self, name, weight):
        self.name = name
        self.assignments = []
        self.weight = weight
        self.total_points_got = 0
        self.total_points_out_of = 0
        self.score = None

    def calc_score(self):
        if self.total_points_out_of == 0:
            self.score = float('nan')
        else:
            self.score = float(self.total_points_got) / float(self.total_points_out_of) * 100

    def reset(self):
        self.assignments = []
        self.total_points_got = 0
        self.total_points_out_of = 0

    def add(self, points_got, points_out_of):
        self.assignments.append((points_got, points_out_of))
        self.total_points_got += points_got
        self.total_points_out_of += points_out_of    

    def drop(self, how_many):
        scores_if_removed = []
        indices_to_remove = []
        for i in range(0, how_many):
            scores_if_removed.append(0)
            indices_to_remove.append(0)
        for i in range(0, len(self.assignments)):
            (a, b) = self.assignments[i]
            min_score = min(scores_if_removed)
            score = float(self.total_points_got - a) / float(self.total_points_out_of - b)
            if score > min_score:
                index = scores_if_removed.index(min_score)
                scores_if_removed[index] = score
                indices_to_remove[index] = i
        indices_to_remove.sort(reverse=True)        
        for index in indices_to_remove:
            a = self.assignments[index]
            print ("Removed {:.2f}/{:.2f} ({:.2f})".format(a[0], a[1], float(a[0]) / float(a[1]) * 100))
            self.assignments.pop(index)
            self.total_points_got -= a[0]
            self.total_points_out_of -= a[1]

class Course:
    def __init__(self, name, num, categories, weights, **kwargs):
        self.name = name
        self.num = num
        self.categories = {}
        self.weights = weights
        self.score = None
        self.weights_sum = None
        self.retrieved = False
        for c, w in zip(categories, weights):
            self.categories[c] = Category(c, w)

    def calc_score(self):
        score = 0
        weights_sum = 0
        for c in self.categories.values():
            c.calc_score()    
            if not math.isnan(c.score):
                score += c.score * float(c.weight)
                weights_sum += c.weight
        self.weights_sum = weights_sum
        self.score = score / weights_sum

    def reset(self):    
        for c in self.categories.values():
            c.reset()

    def enter_class_site(self):
        index = 3 + self.num
        driver.find_element_by_xpath("//div[@id='quickLookup']/table[1]/tbody/tr["+str(index)+"]/td[13]/a").click()

    def load_assignments(self):
        n = driver.execute_script("assignments = document.getElementsByTagName('table')[1].getElementsByTagName('tr'); return assignments.length")
        if n > 3:
            return n
        else:
            time.sleep(1)
            print("...")
            return self.load_assignments()


    def get_grades(self):
        if self.retrieved:
            return
        else:
            self.reset()  

        self.leave_class_site()
        self.enter_class_site()

        n = self.load_assignments()


        for i in range(1, n-2):
            cat = str(driver.execute_script("x = assignments[parseInt("+str(i)+")].getElementsByTagName('td'); return x[1].innerText"))
            if "&amp;" in cat:
                m = cat.index("&amp;")
                cat = cat[:m+1] + cat[m+5:]
            cat = cat.replace(" ","");
            try:
                category = self.categories[cat]
            except:
                continue
            
            points = str(driver.execute_script("return x[10].innerText"))
            if "/" in points:
                points = points.split("/")
            else:
                points = [points, 0] 
            try:
                category.add(float(points[0]), float(points[1]))     
            except:
                continue
        self.retrieved = True
        self.leave_class_site()
        self.calc_score()

    def leave_class_site(self):
        driver.get("https://powerschool.vcs.net/guardian/home.html")

    def calculate_final_needed(self, desired_score):
        final_weight = self.categories["Final?"].weight
        final = (desired_score * 100 - self.score * self.weights_sum) / final_weight
        print ("To get a {:.2f} you need a {:.2f} on the final\n".format(desired_score, final))

    def drop(self, category, how_many):
        category.drop(how_many)
        self.calc_score()

    def show_info(self):
        print ("{:40} {:20} {:20}".format(self.name, "Category Score", "Category Weight"));
        for c in self.categories.values():
            print("{:40} {:<20.2f} {:<20.0f}".format(c.name, c.score, c.weight))
        print str(self.score)+"\n"

    def add_and_update(self, category, points_got, points_out_of):
        category.add(points_got, points_out_of)
        self.calc_score()

#--------------------------------------------------------------------------------

courses = {}
with open('courses.json') as f:
	data = json.load(f)
for course in data.keys():
	courses[course] = Course(**data[course])

#--------------------------------------------------------------------------------


def float_condition(user_input):
    try:
        return float(user_input)
    except:
        return None

def int_condition(user_input):
    try:
        return int(user_input)
    except:
        return None        

def in_dict_condition(user_input, dict):
    dict_key = dict.get(user_input, None)
    return dict_key

def general_input(prompt, condition, **other):
    user_input = raw_input(prompt)
    params = [user_input]
    if "dict" in other:
        params.append(other["dict"])
    while condition(*params) == None:
        if user_input == "exit":
            driver.quit()
            quit()
        if user_input == "help" and "help" in other:
            other["help"]()
        user_input = raw_input(prompt)
        params[0] = user_input
    return condition(*params)

def manual_show_all():
    for course in courses.values():
        course.get_grades()
        course.show_info()

def manual_add_assignment():
    course = general_input("Class: ", in_dict_condition, dict=courses, help=print_course_keys)
    category = general_input("Category: ", in_dict_condition, dict=course.categories, help=course.enter_class_site)
    points_got = general_input("Score: ", float_condition)
    points_out_of = general_input("Out of: ", float_condition)
    course.get_grades()
    course.add_and_update(category, points_got, points_out_of)
    course.show_info()

def manual_show_class():
    course = general_input("Class: ", in_dict_condition, dict=courses, help=print_course_keys)
    course.get_grades()
    course.show_info()

def manual_calculate_final_needed():
    course = general_input("Class: ", in_dict_condition, dict=courses, help=print_course_keys)
    desired_score = general_input("Desired Score: ", float_condition)
    course.get_grades()
    course.calculate_final_needed(desired_score)

def manual_drop():
    course = general_input("Class: ", in_dict_condition, dict=courses, help=print_course_keys)
    category = general_input("Category: ", in_dict_condition, dict=course.categories, help=course.enter_class_site)
    how_many = general_input("How many: ", int_condition)
    course.get_grades()
    course.drop(category, how_many)
    course.show_info()

def manual_refresh():
    course = general_input("Class: ", in_dict_condition, dict=courses, help=print_course_keys)
    course.retrieved = False
    course.get_grades()
    course.show_info()

commands = {
    "add": manual_add_assignment,
    "show": manual_show_class,
    "final": manual_calculate_final_needed,
    "all": manual_show_all,
    "drop": manual_drop,
    "refresh": manual_refresh
    }

def print_command_keys():
    print commands.keys()

def print_course_keys():
    print courses.keys()

def ask_user():
    command = general_input(": ", in_dict_condition, dict=commands, help=print_command_keys)
    return command()


#--------------------------------------------------------------------------------


request = ""
while request != "exit":
	try:
		request = ask_user()
	except Exception as e:
		print(e)
		driver.quit()
		quit()
