Write a backend service that can receive python package install and uninstall events on a specific endpoint named /event. Define a set of query endpoints to allow the user to get some basic metrics about the events the service has received, enriched with package metadata sourced from pypi:

* Receive events using REST to the following specification:

**POST** /event  
   content-type: application/json  
   {  
      "timestamp": "2024-07-24T12:24:29.644186",  
      "package": "requests",  
      "type": "install"  
   }

* Maintain state as you wish, but a simple non persisting in-memory state will suffice for the purpose of this exercise;  
* Retrieve package information from https://pypi.python.org/pypi/{package}/json and return at least the content of info and a list of releases to the user (see below for example);  
* A summary of the events received should also be presented back to the user in the package summary as per below.

**GET** /package/{package:str}  
{  
   "info": {  
       "author": null,  
       *// ...*  
   },  
   "releases": \[  
       "0.1.0",  
       "1.0.0",  
   \],  
   "events": {  
       "install": {  
           "count": 12345,  
           "last": "2024-07-24T12:24:29.644186",  
       },  
       "uninstall": {  
           "count": 12345,  
           "last": "2024-07-24T12:24:29.644186",  
       }  
   },  
}

* Include endpoints that respond to simple questions such as "How many total installs have there been for X package?" and"When was the most recent installation for X package?" as shown below:


**GET** /package/{package:str}/event/install/total  
12345

**GET** /package/{package:str}/event/install/last  
2024-07-24T12:24:29.644186

Having this implemented in Python will be a real plus. Other than that: feel free to choose the stack and tool you feel appropriate for solving this in your usual production standard.  No need to be exhaustive or perfect as long as it shows us how you'd tackle this and how you'd ensure it is high quality and resilient. We will have some time during the interview to discuss your choices and improvements you'd make.