import json

from flask import Flask, jsonify, request, make_response
from flask_restful import Resource, Api, reqparse
import os
import psycopg2
import psycopg2.extras
from datetime import date, datetime
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, JWTManager

app = Flask(__name__)
api = Api(app)

app.config["JWT_SECRET_KEY"] = "super-secret"  # Change this!
jwt = JWTManager(app)

conn = None


def get_db_connection():
    global conn
    if conn is None:
        conn = psycopg2.connect("host=%s user=%s password=%s dbname=%s" % (os.environ['POSTGRES_HOST'],
                                os.environ['POSTGRES_USERNAME'],
                                os.environ['POSTGRES_PASSWORD'],
                                os.environ['POSTGRES_DB']))
        conn.autocommit = True
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    return cursor


class Create(Resource):
    def get(self):
        cur = get_db_connection()
        sql_string = '''CREATE TABLE IF NOT EXISTS users (
                          id int NOT NULL AUTO_INCREMENT,
                          name varchar(25) COLLATE utf8mb4_unicode_ci NOT NULL,
                          surname varchar(25) COLLATE utf8mb4_unicode_ci NOT NULL,
                          password varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
                          mobile_phone_number varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
                          gender int DEFAULT NULL,
                          PRIMARY KEY (id),
                          UNIQUE KEY users_mobile_phone_number_key (mobile_phone_number)
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;'''
        cur.execute(sql_string)


def query_creator(method, table, columns='', values=tuple(), where='id', id=None):
    if method == 'select':
        query = "SELECT * FROM %s" % table
    elif method == 'select_where':
        query = "SELECT * FROM %s WHERE %s = %s" % (table, where, id)
    elif method == 'insert':
        query = "INSERT INTO %s (%s) VALUES %s" % (table, columns, values)
        query += " RETURNING *"
    elif method == 'update':
        update_string = ''
        for idx, col in enumerate(columns.split(', ')):
            val = values[idx]
            if type(val) == str:
                val = "'" + val + "'"
            update_string += col + " = " + val
            if idx != len(columns.split(', ')) - 1:
                update_string = update_string + ', '
        query = "UPDATE %s SET %s WHERE %s = %s" % (table, update_string, where, id)
        print(query)
    elif method == 'delete':
        query = "DELETE FROM %s WHERE %s = %s" % (table, where, id)
    else:
        return None
    return query


def columns_values_creator(columns):
    values = []
    for col in columns:
        values.append(request.form[col])
    columns = ', '.join(columns)
    values = tuple(values)
    return columns, values


def jwt_control(jwt_token):
    try:
        jwt = jwt_token.split(' ')[1]
        phone = get_jwt_identity()
        query = "SELECT * FROM users WHERE mobile_phone_number = '%s'" % phone
        cur = get_db_connection()
        cur.execute(query)
        rows = cur.fetchone()
        if rows is None:
            return False
        return True
    except:
        return False


class Register(Resource):
    def post(self):
        columns = ['name', 'surname', 'password', 'mobile_phone_number', 'gender']
        col_strings, values = columns_values_creator(columns)
        query = query_creator('insert', 'users', col_strings, values)
        cur = get_db_connection()
        cur.execute(query)
        user = cur.fetchone()
        id = user['id']
        phone = request.form['mobile_phone_number']
        access_token = create_access_token(identity=id)
        return {'Status': 201, 'access_token': access_token}


class Login(Resource):
    def post(self):
        phone = request.form['mobile_phone_number']
        password = request.form['password']
        print(phone, password)
        query = "SELECT * FROM users WHERE mobile_phone_number = '%s' AND password = '%s'" % (phone, password)
        cur = get_db_connection()
        cur.execute(query)
        rows = cur.fetchone()
        id = rows['id']
        if rows is None:
            return {'Status': 401, 'message': 'Invalid username or password'}
        access_token = create_access_token(identity=id)
        return {'Status': 200, 'access_token': access_token}


class Users(Resource):

    @jwt_required()
    def get(self):
        current_user = get_jwt_identity()
        print(current_user)
        query = query_creator('select', 'users')
        cur = get_db_connection()
        cur.execute(query)
        rows = cur.fetchall()
        return jsonify(rows)

    @jwt_required()
    def post(self):
        columns = ['name', 'surname', 'password', 'mobile_phone_number', 'gender']
        col_strings, values = columns_values_creator(columns)
        query = query_creator('insert', 'users', col_strings, values)
        cur = get_db_connection()
        cur.execute(query)
        return {'Status': 200}


class User(Resource):
    def get(self, user_id):
        query = query_creator('select_where', 'users', id=user_id)
        cur = get_db_connection()
        cur.execute(query)
        rows = cur.fetchone()
        return jsonify(rows)

    def put(self, user_id):
        columns = ['name', 'surname', 'password', 'mobile_phone_number', 'gender']
        col_strings, values = columns_values_creator(columns)
        query = query_creator('update', 'users', col_strings, values, id=user_id)
        cur = get_db_connection()
        cur.execute(query)
        return {'Status': 200}

    def delete(self, user_id):
        query = query_creator('delete', 'users', id=user_id)

        return {'user': 'user'}


class UserReviews(Resource):
    def get(self, user_id):
        query = query_creator('select_where', 'reviews', id=user_id, where='user_id')
        cur = get_db_connection()
        cur.execute(query)
        rows = cur.fetchall()
        return jsonify(rows)

    def post(self, user_id):
        return {'user_reviews': 'user_reviews'}


class UserReservations(Resource):
    def get(self, user_id):
        query = query_creator('select_where', 'reservations', id=user_id, where='user_id')
        cur = get_db_connection()
        cur.execute(query)
        rows = cur.fetchall()
        return jsonify(rows)

    def post(self, user_id):
        columns = ['waiter_id', 'user_id', 'restaurant_id', 'status', 'reservation_date', 'reservation_hour', 'persons',
                   'reservation_status']
        col_strings, values = columns_values_creator(columns)
        return {'user_reservations': 'user_reservations'}


class UserReservation(Resource):
    def get(self, user_id, reservation_id):
        query = query_creator('select_where', 'reservations', id=reservation_id)
        cur = get_db_connection()
        cur.execute(query)
        rows = cur.fetchone()
        return jsonify(rows)

    def delete(self, user_id, reservation_id):
        query = query_creator('delete', 'reservations', id=reservation_id)
        cur = get_db_connection()
        cur.execute(query)
        return {'Status': 200}


class Restaurants(Resource):
    def get(self):
        query = query_creator('select', 'restaurants')
        cur = get_db_connection()
        cur.execute(query)
        rows = cur.fetchall()
        return jsonify(rows)

    def post(self):
        columns = ['name', 'legal_name', 'photo', 'description', 'address', 'menu_description']
        col_strings, values = columns_values_creator(columns)
        query = query_creator('insert', 'restaurants', col_strings, values)
        cur = get_db_connection()
        cur.execute(query)
        return {'Status': 201}


class Restaurant(Resource):
    def get(self, restaurant_id):
        query = query_creator('select_where', 'restaurants', id=restaurant_id)
        cur = get_db_connection()
        cur.execute(query)
        rows = cur.fetchone()
        return jsonify(rows)

    def put(self, restaurant_id):
        columns = ['name', 'legal_name', 'photo', 'description', 'address', 'menu_description']
        col_strings, values = columns_values_creator(columns)
        query = query_creator('update', 'restaurants', col_strings, values, id=restaurant_id)
        cur = get_db_connection()
        cur.execute(query)
        return {'Status': 200}

    def delete(self, restaurant_id):
        query = query_creator('delete', 'restaurants', id=restaurant_id)
        cur = get_db_connection()
        cur.execute(query)
        return {'Status': 200}


class RestaurantReviews(Resource):
    def get(self, restaurant_id):
        # fetch restaurant and its reviews by join method
        query = query_creator('select_where', 'reviews', id=restaurant_id, where='restaurant_id')
        cur = get_db_connection()
        cur.execute(query)
        rows = cur.fetchall()
        return jsonify(rows)


class RestaurantReservations(Resource):
    def get(self, restaurant_id):
        query = query_creator('select_where', 'reservations', id=restaurant_id)
        cur = get_db_connection()
        cur.execute(query)
        rows = cur.fetchall()
        return jsonify(rows)


class Waiters(Resource):
    def get(self):
        query = query_creator('select', 'waiters')
        cur = get_db_connection()
        cur.execute(query)
        rows = cur.fetchall()
        return jsonify(rows)

    def post(self):
        columns = ['name', 'surname', 'restaurant_id']
        col_strings, values = columns_values_creator(columns)
        query = query_creator('insert', 'waiters', col_strings, values)
        cur = get_db_connection()
        cur.execute(query)
        return {'status': 201}


class Waiter(Resource):
    def get(self, waiter_id):
        query = query_creator('select_where', 'waiters', id=waiter_id)
        cur = get_db_connection()
        cur.execute(query)
        rows = cur.fetchone()
        return jsonify(rows)

    def put(self, waiter_id):
        columns = ['name', 'surname', 'restaurant_id']
        col_strings, values = columns_values_creator(columns)
        query = query_creator('update', 'waiters', col_strings, values, id=waiter_id)
        cur = get_db_connection()
        cur.execute(query)
        return {'status': 200}

    def delete(self, waiter_id):
        query = query_creator('delete', 'waiters', id=waiter_id)
        cur = get_db_connection()
        cur.execute(query)
        return {'status': 200}


class WaiterReviews(Resource):
    def get(self, waiter_id):
        query = query_creator('select_where', 'reviews', id=waiter_id, where='waiter_id')
        cur = get_db_connection()
        cur.execute(query)
        rows = cur.fetchall()
        return jsonify(rows)


class WaiterReservations(Resource):
    def get(self, waiter_id):
        query = query_creator('select_where', 'reservations', id=waiter_id, where='waiter_id')
        cur = get_db_connection()
        cur.execute(query)
        rows = cur.fetchall()
        return jsonify(rows)


class Menu(Resource):
    def get(self, restaurant_id):
        query = query_creator('select_where', 'menu_elements', id=restaurant_id, where='restaurant_id')
        cur = get_db_connection()
        cur.execute(query)
        rows = cur.fetchall()
        return jsonify(rows)


class MenuElements(Resource):
    def get(self, restaurant_id):
        query = query_creator('select_where', 'menu_elements', id=restaurant_id, where='restaurant_id')
        cur = get_db_connection()
        cur.execute(query)
        rows = cur.fetchone()
        return jsonify(rows)

    def post(self, restaurant_id):
        columns = ['name', 'description', 'price', 'photo', 'restaurant_id']
        col_strings, values = columns_values_creator(columns)
        query = query_creator('insert', 'menu_elements', col_strings, values)
        cur = get_db_connection()
        cur.execute(query)
        return {'Status': 201}


class MenuElement(Resource):
    def get(self, restaurant_id, menu_element_id):
        query = query_creator('select_where', 'menu_elements', id=menu_element_id)
        cur = get_db_connection()
        cur.execute(query)
        rows = cur.fetchone()
        return jsonify(rows)

    def put(self, restaurant_id, menu_element_id):
        columns = ['name', 'description', 'price', 'photo']
        col_strings, values = columns_values_creator(columns)
        query = query_creator('update', 'menu_elements', col_strings, values, id=menu_element_id)
        cur = get_db_connection()
        cur.execute(query)
        return {'Status': 200}

    def delete(self, restaurant_id, menu_element_id):
        query = query_creator('delete', 'menu_elements', id=menu_element_id)
        cur = get_db_connection()
        cur.execute(query)
        return {'Status': 200}


class Reviews(Resource):
    def get(self):
        query = query_creator('select', 'reviews')
        cur = get_db_connection()
        cur.execute(query)
        rows = cur.fetchall()
        return jsonify(rows)

    def post(self):
        columns = ['reservation_id', 'comment', 'rating']
        col_strings, values = columns_values_creator(columns)
        query = query_creator('insert', 'reviews', col_strings, values)
        cur = get_db_connection()
        cur.execute(query)
        return {'Status': 201}


class Review(Resource):
    def get(self, review_id):
        query = query_creator('select_where', 'reviews', id=review_id)
        cur = get_db_connection()
        cur.execute(query)
        rows = cur.fetchone()
        return jsonify(rows)

    def put(self, review_id):
        columns = ['reservation_id', 'comment', 'rating']
        col_strings, values = columns_values_creator(columns)
        query = query_creator('update', 'reviews', col_strings, values, id=review_id)
        cur = get_db_connection()
        cur.execute(query)
        return {'Status': 200}

    def delete(self, review_id):
        query = query_creator('delete', 'reviews', id=review_id)
        cur = get_db_connection()
        cur.execute(query)
        return {'Status': 200}


class Reservations(Resource):
    def get(self):
        query = query_creator('select', 'reservations')
        cur = get_db_connection()
        cur.execute(query)
        rows = cur.fetchall()
        for row in rows:
            row['reservation_date'] = row['reservation_date'].strftime("%Y-%m-%d")
            row['reservation_hour'] = row['reservation_hour'].strftime("%H:%M")
        print(rows[0])
        return jsonify(rows)

    def post(self):
        columns = ['waiter_id', 'user_id', 'restaurant_id', 'status', 'reservation_date', 'reservation_hour', 'persons',
                   'reservation_status']
        reservation_hour = request.form['reservation_hour']
        reservation_date = request.form['reservation_date']
        restaurant_id = request.form['restaurant_id']
        if if_reservation_available(self, reservation_date, reservation_hour, restaurant_id):
            col_strings, values = columns_values_creator(columns)
            query = query_creator('insert', 'reservations', col_strings, values)
            cur = get_db_connection()
            cur.execute(query)
            return {'Status': 201}
        else:
            return {'Status': 400, 'message': 'Reservation is not available'}


class Reservation(Resource):
    def get(self, reservation_id):
        query = query_creator('select_where', 'reservations', id=reservation_id)
        cur = get_db_connection()
        cur.execute(query)
        rows = cur.fetchone()
        rows['reservation_date'] = rows['reservation_date'].strftime("%Y-%m-%d")
        rows['reservation_hour'] = rows['reservation_hour'].strftime("%H:%M")
        return jsonify(rows)

    def put(self, reservation_id):
        columns = ['waiter_id', 'user_id', 'restaurant_id', 'status', 'reservation_date', 'reservation_hour', 'persons',
                   'reservation_status']
        reservation_hour = request.form['reservation_hour']
        reservation_date = request.form['reservation_date']
        restaurant_id = request.form['restaurant_id']
        if if_reservation_available(self, reservation_date, reservation_hour, restaurant_id, reservation_id):
            col_strings, values = columns_values_creator(columns)
            query = query_creator('update', 'reservations', col_strings, values, id=reservation_id)
            cur = get_db_connection()
            cur.execute(query)
            return {'Status': 201}
        else:
            return {'Status': 400, 'message': 'Reservation is not available'}

    def delete(self, reservation_id):
        query = query_creator('delete', 'reservations', id=reservation_id)
        cur = get_db_connection()
        cur.execute(query)
        return {'Status': 200}


class Test(Resource):
    def get(self):
        print(timeDiffInMinutes('12:00', '13:00'))
        reservation_date = '2022-01-01'
        reservation_hour = '12:00'
        print(if_reservation_available(self, reservation_date, reservation_hour, 1))
        return 1


def timeDiffInMinutes(time1, time2):
    FMT = '%H:%M'
    tdelta = datetime.strptime(time2, FMT) - datetime.strptime(time1, FMT)
    tdelta = tdelta.seconds / 60
    return tdelta


def if_reservation_available(self, reservation_date, reservation_hour, restaurant_id, reservation_id=None):
    query = query_creator('select_where', 'reservations', id=restaurant_id, where='restaurant_id')
    query = query + " AND reservation_date = '%s'" % reservation_date
    if reservation_id is not None:
        query = query + " AND id != %s" % reservation_id
    cur = get_db_connection()
    print(query)
    cur.execute(query)
    rows = cur.fetchall()
    for row in rows:
        print('tdelta', timeDiffInMinutes(row['reservation_hour'].strftime("%H:%M"), reservation_hour))
        if timeDiffInMinutes(row['reservation_hour'].strftime("%H:%M"), reservation_hour) < 60:
            return False
    return True


# User +
# Restaurant+
# Waiter +
# Menu +
# MenuElement +
# Review +
# Reservation+


api.add_resource(Test, '/test')
api.add_resource(Users, '/users')
api.add_resource(Login, '/users/login')
api.add_resource(Register, '/users/register')
api.add_resource(User, '/users/<user_id>')
api.add_resource(UserReviews, '/users/<user_id>/reviews')
api.add_resource(UserReservations, '/users/<user_id>/reservations')  # user reservations
api.add_resource(UserReservation, '/users/<user_id>/reservations/<reservation_id>')

api.add_resource(Restaurants, '/restaurants')
api.add_resource(Restaurant, '/restaurants/<restaurant_id>')
api.add_resource(Menu,
                 '/restaurants/<restaurant_id>/menu')  # See the restaurant menu or Create menu if there is no menu
api.add_resource(MenuElements, '/restaurants/<restaurant_id>/menu/menu-element')  # Update or Delete or Add menu element
api.add_resource(MenuElement,
                 '/restaurants/<restaurant_id>/menu/menu-element/<menu_element_id>')  # Update or Delete or Add menu element
api.add_resource(RestaurantReviews, '/restaurants/<restaurant_id>/reviews')  # See the restaurant reviews
api.add_resource(RestaurantReservations, '/restaurants/<restaurant_id>/reservations')  # See the restaurant reservations

api.add_resource(Reviews, '/reviews')
api.add_resource(Review, '/reviews/<review_id>')

api.add_resource(Reservations, '/reservations')
api.add_resource(Reservation, '/reservations/<reservation_id>')

api.add_resource(Waiters, '/waiters')
api.add_resource(Waiter, '/waiters/<waiter_id>')
api.add_resource(WaiterReviews, '/waiters/<waiter_id>/reviews')
api.add_resource(Create, '/db')

@app.route('/test1', methods=['GET'])
def test1():
   return make_response(jsonify({'message': 'test route'}), 200)

if os.environ['IS_PROD'] == 1:
    app.run(debug=False, host='0.0.0.0', port=5000)
elif __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)


