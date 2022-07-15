import sys
import requests
from pprint import pprint
URL = 'http://127.0.0.1:8001/graphql'
BARFIURL = 'http://barfi.youtility.in:8000/graphql'

class graphQL:
    headers = {}


    def run_query(self, query, variables=None):# A simple function to use requests.post to make the API call. Note the json= section.
        request = requests.post(BARFIURL, json={'query': query, 'variables': variables}, headers=self.headers)
        if request.status_code != 200:
            raise Exception(f"Query failed to run by returning code of {request.status_code}. {query}")
        pprint(request.json())

    def login(self):
        query = """
        mutation TokenAuth{
            tokenAuth(input:{
                deviceid:"fakedeviceid",
                loginid:"naveen",
                sitecode:"ICICIBANK.MANIPUR",
                password:"naveen@youtility" }) {
                token
                payload
            }
        }
        """
        self.run_query(query=query)


    def logout(self):
        query = """
        mutation logout{
            logoutUser{
                status
                msg
            }
        }
        """
        self.run_query(query=query)



if __name__ == '__main__':
    gql = graphQL()
    gql.login()
