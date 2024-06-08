import sqlite3
from datetime import date, datetime

class DBRequests:
    def __init__(self, db):
        self.__db = db
        self.__cur = db.cursor()

    def addUser(self, surname, name, number, passwd):
        try:
            self.__cur.execute("INSERT INTO users VALUES(NULL, ?, ?, ?, ?)", (name, surname, number, passwd,))
            self.__db.commit()
        except sqlite3.Error as e:
            print("Ошибка при добавлении пользователя: " + str(e))

    def getUserByPhone(self, phone):
        try:
            self.__cur.execute("SELECT * FROM users WHERE number = ?", (phone,))
            user = self.__cur.fetchone()
            return user
        except sqlite3.Error as e:
            print("Ошибка поиска пользователя: " + str(e))
            return False

    def addRequest(self, user_id, service_id, address, latitude, longitude, status, description):
        try:
            current_time = datetime.now().strftime("%H:%M %d-%m-%y")
            self.__cur.execute("INSERT INTO applications VALUES(NULL, ?, ?, ?, ?, ?, ?, ?, ?)",
                               (user_id, service_id, address, latitude, longitude, status, description, current_time))
            self.__db.commit()
        except sqlite3.Error as e:
            print("Ошибка при добавлении заявки: " + str(e))

    def updateRequest(self, application_id, status, description):
        try:
            self.__cur.execute("UPDATE applications SET status=?, description=? WHERE id=?", (status, description, application_id,))
            self.__db.commit()
        except sqlite3.Error as e:
            print("Ошибка при отзыве заявки: " + str(e))

    def updateRequestStatus(self, application_id, status):
        try:
            self.__cur.execute("UPDATE applications SET status=? WHERE id=?", (status, application_id,))
            self.__db.commit()
        except sqlite3.Error as e:
            print("Ошибка при обновлении статуса: " + str(e))

    def getRequests(self, user_id):
        try:
            self.__cur.execute("SELECT * FROM applications WHERE user_id = ?", (user_id,))
            services = self.__cur.fetchall()
            return services
        except sqlite3.Error as e:
            print("Ошибка получения заявок для пользователя: " + str(e))

    def getServiceNameById(self, service_id):
        try:
            self.__cur.execute("SELECT name FROM services WHERE id = ?", (service_id,))
            service_name = self.__cur.fetchone()
            return service_name[0]
        except sqlite3.Error as e:
            print("Ошибка: " + str(e))

    def getUserById(self, id):
        try:
            self.__cur.execute("SELECT * FROM users WHERE id = ?", (id,))
            user = self.__cur.fetchone()
            return user
        except sqlite3.Error as e:
            print("Ошибка взятия пользователя из базы по айди!")
            return False

    def getServices(self):
        try:
            self.__cur.execute("SELECT name, price FROM services")
            services = self.__cur.fetchall()
            return services
        except sqlite3.Error as e:
            print("Ошибка при выводе списка услуг: " + str(e))
            return []
