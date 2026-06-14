from db_helper import get_db_connection

connection, cursor = get_db_connection()

print("Database and table created successfully")
connection.close()