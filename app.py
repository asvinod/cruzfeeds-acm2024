import random
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Load food data from CSV
def load_food_data():
    df = pd.read_csv('jrlc9.csv')
    return df

# Function to get dietary restrictions from CSV
def get_dietary_restrictions():
    df = pd.read_csv('dietary_restrictions.csv')
    return df['restriction'].tolist()

def generate_meal_combinations(caloric_goal, meal_type, selected_restrictions):
    df = load_food_data()

    # Filter based on Meal_Type
    df = df[df['Meal_Type'] == meal_type]
    print(f"After filtering by meal_type '{meal_type}': {len(df)} items remaining.")

    # Convert selected restrictions into a list
    list_restrictions = selected_restrictions.split(",") if selected_restrictions else []
    print("List restrictions: ", list_restrictions)

    # Apply filters based on selected restrictions
    # Apply filters based on selected restrictions
    if list_restrictions:
        for restriction in list_restrictions:
            if restriction == 'vegetarian':
                df = df[df['Restrictions'].str.contains('vegetarian', case=False)]
            elif restriction == 'vegan':
                df = df[df['Restrictions'].str.contains('vegan', case=False)]
            elif restriction in ['eggs', 'egg']:
                df = df[~df['Food_Item'].str.contains('egg', case=False)]  # Exclude items with "egg"
            elif restriction in ['milk', 'dairy']:
                df = df[~df['Food_Item'].str.contains('milk|cheese|butter', case=False)]  # Exclude dairy items
            elif restriction in ['soy']:
                df = df[~df['Food_Item'].str.contains('soy', case=False)]  # Exclude soy items
            elif restriction in ['nuts']:
                df = df[~df['Food_Item'].str.contains('nut|peanut|almond', case=False)]  # Exclude nut items
            elif restriction in ['gluten']:
                df = df[~df['Food_Item'].str.contains('gluten|wheat', case=False)]  # Exclude gluten items
            else:
                # Exclude any items that contain the restricted ingredient
                df = df[~df['Food_Item'].str.contains(restriction, case=False)]

    print(f"After applying dietary restrictions: {len(df)} items remaining.")

    # Filter food items by category (Protein, Grain, Vegetable, Dessert)
    proteins = df[df['Category'] == 'P']
    grains = df[df['Category'] == 'G']
    vegetables = df[df['Category'] == 'V']
    desserts = df[df['Category'] == 'D']

    # Add default items if no options are available
    if proteins.empty:
        proteins = pd.DataFrame({'Food_Item': ['Tofu'], 'Calories': [94], 'Category': ['P']})
    if grains.empty:
        grains = pd.DataFrame({'Food_Item': ['Whole Wheat Bread'], 'Calories': [80], 'Category': ['G']})
    if vegetables.empty:
        vegetables = pd.DataFrame({'Food_Item': ['Simple Salad'], 'Calories': [50], 'Category': ['V']})

    print(f"Proteins: {len(proteins)}, Grains: {len(grains)}, Vegetables: {len(vegetables)}, Desserts: {len(desserts)}")

    # Generate possible meal combinations
    meal_options = []

    # Iterate through combinations of Protein, Grain, and Vegetable
    for p in proteins.itertuples():
        for g in grains.itertuples():
            for v in vegetables.itertuples():
                total_calories = p.Calories + g.Calories + v.Calories

                # Optionally add Dessert if total calories with dessert are under the goal
                for d in desserts.itertuples():
                    dessert_total = total_calories + d.Calories
                    if dessert_total <= caloric_goal:
                        meal_options.append({
                            'protein': p.Food_Item,
                            'grain': g.Food_Item,
                            'vegetable': v.Food_Item,
                            'dessert': d.Food_Item,
                            'total_calories': dessert_total
                        })

                # Add non-dessert meals if the caloric goal is met
                if total_calories <= caloric_goal:
                    meal_options.append({
                        'protein': p.Food_Item,
                        'grain': g.Food_Item,
                        'vegetable': v.Food_Item,
                        'total_calories': total_calories
                    })

    print(f"Generated {len(meal_options)} meal options.")
    return meal_options

# Calculate BMR and daily calories for macros
def calculate_bmr_and_macros(user_info):
    weight_kg = user_info['weight'] * 0.453592
    height_cm = user_info['height'] * 2.54
    bmr = (655.1 if user_info['sex'] == 'female' else 66.47) + \
          (9.563 if user_info['sex'] == 'female' else 13.75) * weight_kg + \
          (1.850 if user_info['sex'] == 'female' else 5.003) * height_cm - \
          (4.676 if user_info['sex'] == 'female' else 6.755) * user_info['age']

    activity_multiplier = {
        'sedentary': 1.2, 'lightly active': 1.375, 'moderately active': 1.55,
        'active': 1.725, 'extremely active': 1.9
    }.get(user_info['activity_level'], 1.2)

    daily_calories = bmr * activity_multiplier + \
        (500 if user_info['goal'] == 'gain' else -500 if user_info['goal'] == 'lose' else 0)
    
    return daily_calories

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        dining_hall = request.form.get('dininghall')
        return redirect(url_for('dietary'))  # Redirect to dietary restrictions page
    return render_template('index.html')

@app.route('/dietary', methods=['GET', 'POST'])
def dietary():
    restrictions = get_dietary_restrictions()  # Load the restrictions
    if request.method == 'POST':
        selected_restrictions = request.form.getlist('restrictions')
        print(f"Selected restrictions before redirect: {selected_restrictions}")  # Debug print
        
        # Save selected restrictions and redirect to input_data
        return redirect(url_for('input_data', selected_restrictions=','.join(selected_restrictions)))
    return render_template('dietary.html', restrictions=restrictions)

@app.route('/input_data', methods=['GET', 'POST'])
def input_data():
    selected_restrictions = request.args.get('selected_restrictions', '').split(',')  # Get restrictions from the URL
    print(f"Selected restrictions in input_data: {selected_restrictions}")  # Debug print

    if request.method == 'POST':
        # Check if the Skip button was pressed
        if 'skip' in request.form:
            caloric_goal = 800  # Default caloric goal if skipped
            return redirect(url_for('meal_selection', caloric_goal=caloric_goal, selected_restrictions=','.join(selected_restrictions)))  # Redirect to meal selection page
        
        # Only try to process the form if the Skip button was NOT pressed
        else:
            try:
                # Handle height, weight, sex, and age inputs here
                weight = float(request.form.get('weight', 0))  # Default to 0 if empty
                height = float(request.form.get('height', 0))  # Default to 0 if empty
                sex = request.form.get('sex', '').lower()
                age = int(request.form.get('age', 0))  # Default to 0 if empty
                activity_level = request.form.get('activity_level', '')  # Optional field, handle accordingly
                goal = request.form.get('goal', '')  # Optional field, handle accordingly

                # Create user_info dict
                user_info = {
                    'weight': weight,
                    'height': height,
                    'sex': sex,
                    'age': age,
                    'activity_level': activity_level,
                    'goal': goal,
                    'selected_restrictions': selected_restrictions  # Include selected restrictions here
                }

                # Assuming calculate_bmr_and_macros function handles the logic correctly
                caloric_goal = calculate_bmr_and_macros(user_info)  # Calculate caloric goal
                return redirect(url_for('goal', caloric_goal=caloric_goal, selected_restrictions=','.join(selected_restrictions)))  # Redirect to goal selection page

            except ValueError:
                # Handle invalid input, possibly redirect back with an error message
                return "Invalid input, please enter valid numbers.", 400

    return render_template('calorie_calculator.html', selected_restrictions=selected_restrictions)



@app.route('/goal', methods=['GET', 'POST'])
def goal():
    caloric_goal = request.args.get('caloric_goal', default=800, type=int)  # Get the caloric goal from URL parameters
    selected_restrictions = request.args.get('selected_restrictions', '')  # Get the selected restrictions

    if request.method == 'POST':
        selected_goal = request.form.get('goal')
        return redirect(url_for('meal_selection', caloric_goal=caloric_goal, selected_restrictions=selected_restrictions))  # Redirect to meal selection page

    return render_template('goal.html', caloric_goal=caloric_goal)

@app.route('/meal_selection', methods=['GET', 'POST'])
def meal_selection():
    caloric_goal = request.args.get('caloric_goal', default=800, type=int)  # Get the caloric goal from URL parameters
    selected_restrictions = request.args.get('selected_restrictions', '').split(',')  # Get the selected restrictions

    if request.method == 'POST':
        selected_meal = request.form.get('meal')
        return redirect(url_for('meal_plan', caloric_goal=caloric_goal, meal_type=selected_meal, selected_restrictions=','.join(selected_restrictions)))  # Redirect to the meal plan page

    return render_template('meal_selection.html', selected_restrictions=selected_restrictions)  # Pass selected restrictions to template


@app.route('/meal_plan', methods=['GET', 'POST'])
def meal_plan():
    caloric_goal = request.args.get('caloric_goal', default=800, type=int)  # Get the caloric goal from URL parameters
    meal_type = request.args.get('meal_type', default='lunch')  # Get the selected meal type from URL parameters
    selected_restrictions = request.args.get('selected_restrictions', '')#.split(',')  # Get selected restrictions
    print(f"Selected restrictions in meal_plan: {selected_restrictions}")  # Debug print

    meal_options = generate_meal_combinations(caloric_goal, meal_type, selected_restrictions)
    
    return render_template('meal_plan.html', meal_options=meal_options)  # Pass meal options to template

if __name__ == '__main__':
    app.run(debug=True)