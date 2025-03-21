import psycopg2
from tabulate import tabulate
from datetime import datetime
import re
from pyshorteners import Shortener

class RestaurantUI:
    def __init__(self):
        self.db_params = {
            'dbname': 'restaurant_db',
            'user': 'jh',
            'password': '12345678',
            'host': 'localhost',
            'port': '5432'
        }
        self.conn = None
        self.shortener = Shortener()

    def connect_db(self):
        """Establish database connection"""
        if not self.conn:
            self.conn = psycopg2.connect(**self.db_params)

    def close_db(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    def get_sort_order(self):
        """Get user's preferred sort order"""
        while True:
            print("\nSort by:")
            print("1. Rating (highest first)")
            print("2. Price (lowest first)")
            print("3. Price (highest first)")
            
            choice = input("Enter your choice (1-3): ").strip()
            
            if choice == '1':
                return "ORDER BY rating DESC, review_count DESC"
            
            elif choice == '2':
                # Sorting price range from '$' -> lowest to '$$$$' -> highest
                return """
                    ORDER BY 
                    CASE price_range 
                        WHEN '$' THEN 1 
                        WHEN '$$ - $$$' THEN 2 
                        WHEN '$$$$' THEN 3 
                        ELSE 4 -- Handle unexpected values
                    END, rating DESC
                """
            
            elif choice == '3':
                # Sorting price range from '$$$$' -> highest to '$' -> lowest
                return """
                    ORDER BY 
                    CASE price_range 
                        WHEN '$' THEN 1 
                        WHEN '$$ - $$$' THEN 2 
                        WHEN '$$$$' THEN 3 
                        ELSE 4 -- Handle unexpected values
                    END DESC, rating DESC
                """
            
            else:
                print("Invalid choice. Please try again.")


    def get_restaurants(self, city, food_type=None, sort_order="ORDER BY rating DESC", limit=10):
        """Get restaurants based on city and optional food type"""
        with self.conn.cursor() as cur:
            if food_type:
                query = f"""
                    SELECT name, rating, review_count, type, price_range, 
                           street_address, location, contact_number, trip_advisor_url
                    FROM restaurants
                    WHERE city ILIKE %s AND type ILIKE %s
                    {sort_order}
                    LIMIT %s;
                """
                cur.execute(query, (f"%{city}%", f"%{food_type}%", limit))
            else:
                query = f"""
                    SELECT name, rating, review_count, type, price_range, 
                           street_address, location, contact_number, trip_advisor_url
                    FROM restaurants
                    WHERE city ILIKE %s
                    {sort_order}
                    LIMIT %s;
                """
                cur.execute(query, (f"%{city}%", limit))
            return cur.fetchall()

    def validate_required_input(self, prompt, field_name):
        """Get and validate required input"""
        while True:
            value = input(prompt).strip()
            if value:
                return value
            print(f"{field_name} cannot be empty. Please try again.")

    def add_review(self):
        """Add a new restaurant review to the database"""
        print("\n=== Add New Restaurant Review ===")
        
        # Collect required restaurant information with validation
        name = self.validate_required_input("Restaurant Name: ", "Restaurant name")
        street = self.validate_required_input("Street Address: ", "Street address")
        city = self.validate_required_input("City: ", "City")
        location = self.validate_required_input("Full Location (e.g., San Francisco, CA 12345): ", "Location")
        restaurant_type = self.validate_required_input("Restaurant Type (e.g., Italian, Seafood): ", "Restaurant type")
        
        # Validate and get rating
        while True:
            try:
                rating = float(input("Rating (0.0-5.0): "))
                if 0 <= rating <= 5:
                    break
                print("Rating must be between 0 and 5")
            except ValueError:
                print("Please enter a valid number")
        
        # Validate and get review count
        while True:
            try:
                review_count = int(input("Number of Reviews: "))
                if review_count >= 0:
                    break
                print("Review count must be positive")
            except ValueError:
                print("Please enter a valid number")
        
        # Get required contact information
        contact = self.validate_required_input("Contact Number (e.g., +1 123-456-7890): ", "Contact number")
        
        # Get optional URL and menu
        url = input("TripAdvisor URL (optional): ").strip()
        menu = input("Menu URL (optional): ").strip()
        
        # Get price range
        while True:
            price_range = self.validate_required_input("Price Range ($, $$ - $$$, $$$, or $$$$): ", "Price range")
            if re.match(r'\${1,4}$|\$\$-\$\$\$', price_range):
                break
            print("Please enter a valid price range ($, $$ - $$$, $$$, or $$$$)")

        try:
            with self.conn.cursor() as cur:
                # Get the next available ID
                cur.execute("SELECT MAX(id) FROM restaurants")
                max_id = cur.fetchone()[0] or 0
                new_id = max_id + 1

                # Insert new restaurant
                cur.execute("""
                    INSERT INTO restaurants (
                        id, name, street_address, location, type, rating, 
                        review_count, contact_number, trip_advisor_url,
                        menu, price_range, city, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    new_id, name, street, location, restaurant_type, rating,
                    review_count, contact, url, menu, price_range, city,
                    datetime.now()
                ))
                self.conn.commit()
                print("\nRestaurant review added successfully!")
                
        except Exception as e:
            print(f"Error adding review: {e}")
            self.conn.rollback()

    def shorten_url(self, url):
        """Shorten URL using pyshorteners"""
        if not url or url.lower() == 'check the website for a menu':
            return 'N/A'
        try:
            return self.shortener.tinyurl.short(url)
        except:
            return url

    def display_restaurants(self, restaurants):
        """Display restaurant results in a formatted table"""
        if not restaurants:
            print("\nNo restaurants found")
            return
            
        # Process the results to include shortened URLs
        formatted_results = []
        for restaurant in restaurants:
            row_list = list(restaurant)
            # Shorten the URL (last element in the row)
            row_list[-1] = self.shorten_url(row_list[-1])
            formatted_results.append(row_list)
            
        headers = ['Name', 'Rating', 'Reviews', 'Type', 'Price', 'Address', 'Location', 'Phone', 'URL']
        print(f"\nTop 10 Restaurants:")
        print(tabulate(formatted_results, headers=headers, tablefmt='grid'))

    def delete_restaurant(self, name):
        """Delete a restaurant by its name"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM restaurants WHERE name = %s", (name,))
                if cur.rowcount > 0:
                    self.conn.commit()
                    print(f"\nRestaurant '{name}' has been successfully deleted.")
                else:
                    print(f"\nNo restaurant found with the name '{name}'.")
        except Exception as e:
            print(f"Error deleting restaurant: {e}")
            self.conn.rollback()

    def run(self):
        """Main UI loop"""
        try:
            self.connect_db()
            
            while True:
                print("\n=== Restaurant Recommendation System ===")
                print("1. Search restaurants")
                print("2. Add new restaurant review")
                print("3. Exit")

                choice = input("\nEnter your choice (1-3): ").strip()
                
                if choice == '1':
                    city = self.validate_required_input("\nEnter city name: ", "City name")
                    
                    # Ask if user wants to filter by type
                    filter_type = input("\nWould you like to filter by food type? (y/n): ").strip().lower()
                    food_type = None
                    if filter_type == 'y':
                        food_type = self.validate_required_input("Enter food type (e.g., Italian, Seafood): ", "Food type")
                    
                    sort_order = self.get_sort_order()
                    restaurants = self.get_restaurants(city, food_type, sort_order)
                    self.display_restaurants(restaurants)
                
                elif choice == '2':
                    self.add_review()
                
                elif choice == '3':
                    print("\nGoodbye!")
                    break
                
                else:
                    print("\nInvalid choice. Please try again.")
                
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            self.close_db()

if __name__ == "__main__":
    ui = RestaurantUI()
    ui.run()