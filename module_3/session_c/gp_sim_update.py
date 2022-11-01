#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue 1st Nov

@author: Commodore 64
"""

import simpy
import random
from statistics import mean # this allows us to take a mean of a list easily
import matplotlib.pyplot as plt
import csv
import pandas as pd

# Arrivals generator function
def patient_generator_gp(env, gp_inter, mean_register,
                        mean_consult, mean_book_test, receptionist,
                        gp_doctor):
    p_id = 0
    
    while True:
        # Create new instance of activity generator
        p = activity_generator_gp(env, mean_register, mean_consult, mean_book_test, 
            receptionist, gp_doctor, p_id)
        
        # Run the activity generator
        env.process(p)
        
        # Sample time to next arrival
        t = random.expovariate(1.0 / gp_inter)
        
        # Freeze until time elapsed
        yield env.timeout(t)
        
        p_id += 1

# Calls generator function
def patient_generator_calls(env, call_inter, mean_call_answer, receptionist):
    p_id = 0
    
    while True:
        # Create new instance of activity generator
        p = activity_generator_calls(env, mean_call_answer, receptionist, p_id)
        
        # Run the activity generator
        env.process(p)
        
        # Sample time to next arrival
        t = random.expovariate(1.0 / call_inter)
        
        # Freeze until time elapsed
        yield env.timeout(t)
        
        p_id += 1

# Activity generator function
def activity_generator_gp(env, mean_register, mean_consult, mean_book_test, 
            receptionist, gp_doctor, p_id):
    time_entered_queue_for_registration = env.now
    global list_of_queuing_times_registration
    global list_of_queueing_times_gp
    global list_of_test_booking_times
    global list_of_patient_total_time
    
    # Request a receptionist
    with receptionist.request() as req:
        # Freeze until the request can be met
        yield req
        
        time_left_queue_for_registration = env.now        
        time_in_queue_for_registration = (time_left_queue_for_registration -
                                          time_entered_queue_for_registration)
        print (f"Patient {p_id} queued for registration for",
               f"{time_in_queue_for_registration:.1f} minutes.")

        list_of_queuing_times_registration.append(time_in_queue_for_registration)
        
        # Sample the time spent in registration
        sampled_registration_time = random.expovariate(1.0 / mean_register)
        
        # Freeze until that time has elapsed
        yield env.timeout(sampled_registration_time)
        
    # Here, we're outside of the with statement, and so have just finished
    # with the receptionist.  Which means we've started queuing for the nurse.
    # So we just do exactly as we did before for the next activity in our
    # system.
    time_entered_queue_for_consult = env.now
    
    # Request a doctor
    with gp_doctor.request() as req:
        # Freeze until the request can be met
        yield req

        time_left_queue_for_consult = env.now
        time_in_queue_for_consult = (time_left_queue_for_consult -
                                    time_entered_queue_for_consult)
        print (f"Patient {p_id} queued for consultation for",
               f"{time_in_queue_for_consult:.1f} minutes.")

        list_of_queueing_times_gp.append(time_in_queue_for_consult)
        
        # Sample the time spent in consultation
        sampled_consult_time = random.expovariate(1.0 / mean_consult)
        
        # Freeze until that time has elapsed
        yield env.timeout(sampled_consult_time)
        
    # We now encounter a branching path.  Some patients will be sent for 
    # tests, and others will get assessment.  Remember, a uniform distribution is
    # one in which there's an equal probability of any value being selected.
    # Therefore, we can randomly draw a number between 0 and 1, and compare
    # that number against a threshold.
    decide_test_branch = random.uniform(0,1)
    
    # Then we can just use simple conditional logic to determine the next
    # activity for this patient.  Here, we assume that 20% of patients will
    # be sent to the ACU.
    if decide_test_branch <= 0.25:
        # If the patient has gone down this path then they're now queuing for
        # an initial assessment in the ACU
        time_entered_queue_for_receptionist_test = env.now
        
        # Request an ACU doctor
        with receptionist.request() as req:
            # Freeze until the request can be met
            yield req
            
            time_left_queue_for_receptionist_test = env.now
            time_in_queue_for_receptionist_test = (
                time_left_queue_for_receptionist_test -
                time_entered_queue_for_receptionist_test)
            print (f"Patient {p_id} queued to book test for",
                   f"{time_in_queue_for_receptionist_test:.1f} minutes.")

            list_of_test_booking_times.append(time_in_queue_for_receptionist_test)
            
            # Sample the time spent booking test
            sampled_booking_time = random.expovariate(1.0 / mean_book_test)
            
            # Freeze until that time has elapsed
            yield env.timeout(sampled_booking_time)

    time_in_system = env.now - time_entered_queue_for_registration

    list_of_patient_total_time.append(time_in_system)

# Call activity generator function
def activity_generator_calls(env, mean_call_answer, receptionist, p_id):
    global list_of_queuing_times_call

    time_entered_queue_for_call = env.now
    
    with receptionist.request() as req:
        # Freeze until the request can be met
        yield req
        
        time_left_queue_for_call = env.now        
        time_in_queue_for_call = (time_left_queue_for_call -
                                          time_entered_queue_for_call)
        print (f"Patient {p_id} queued for call for",
               f"{time_in_queue_for_call:.1f} minutes.")

        list_of_queuing_times_call.append(time_in_queue_for_call)
        
        # Sample the time spent in registration
        sampled_call_time = random.expovariate(1.0 / mean_call_answer)
        
        # Freeze until that time has elapsed
        yield env.timeout(sampled_call_time)

# Set up number of times to the run the simulation
number_of_simulation_runs = 100

# Create a file to store the results of each run, and write the column headers
with open("clinic_results.csv", "w") as f:
    writer = csv.writer(f, delimiter=",")
    
    writer.writerow(["Run", "Length of stay"])

# Run the simulation the number of times specified, storing the results of each
# run to file
for run in range(number_of_simulation_runs):

    # Set up simulation environment
    env = simpy.Environment()

    # Set up resources
    receptionist = simpy.Resource(env, capacity=1)
    gp_doctor = simpy.Resource(env, capacity=2)

    # Set up parameter values
    gp_inter = 3
    call_inter = 10
    mean_register = 2
    mean_consult = 8
    mean_book_test = 4
    mean_call_answer = 4

    list_of_queuing_times_registration = []
    list_of_queueing_times_gp = []
    list_of_test_booking_times = []
    list_of_patient_total_time = []
    list_of_queuing_times_call = []

    # Start the arrivals generator
    env.process(patient_generator_gp(env, gp_inter, mean_register,
                            mean_consult, mean_book_test, receptionist,
                            gp_doctor))
    env.process(patient_generator_calls(env, call_inter, mean_call_answer, receptionist))

    # Run the simulation
    env.run(until=480)

    mean_time_in_system = mean(list_of_patient_total_time)

    print ("Mean time in clinic (mins) :",
          f"{mean_time_in_system:.2f}")
    
    # Set up list to write to file - here we'll store the run number alongside
    # the mean queuing time for the nurse in that run
    list_to_write = [run, mean_time_in_system]
    
    # Store the run results to file.  We need to open in append mode ("a"),
    # otherwise we'll overwrite the file each time.  That's why we set up the
    # new file before the for loop, to start anew for each batch of runs
    with open("clinic_results.csv", "a") as f:
        writer = csv.writer(f, delimiter=",")
        
        writer.writerow(list_to_write)
        
# After the batch of runs is complete, we might want to read the results back
# in and take some summary statistics
# Here, we're going to use a neat shortcut for easily reading a csv file into
# a pandas dataframe
results_df = pd.read_csv("clinic_results.csv")

"""

mean_queue_time_registration = mean(list_of_queuing_times_registration)
print (f"Mean queuing time for registration (mins) : {mean_queue_time_registration:.2f}")

mean_queue_time_gp = mean(list_of_queueing_times_gp)
print (f"Mean queuing time for GP (mins) : {mean_queue_time_gp:.2f}")

mean_test_booking_times = mean(list_of_test_booking_times)
print (f"Mean queuing time for booking test (mins) : {mean_test_booking_times:.2f}")

mean_call_booking_times = mean(list_of_queuing_times_call)
print (f"Mean answering call time (mins) : {mean_call_booking_times:.2f}")

fig, ax = plt.subplots()

counts = [mean_queue_time_registration, mean_queue_time_gp, mean_test_booking_times,
            mean_call_booking_times]

names = ["Registration", "Consult", "Book test", "Answer phone"]

ax.bar(names, counts)

plt.show()

list_of_patient_total_time

mean_time_in_system = mean(list_of_patient_total_time)
print (f"Mean time in system (mins) : {mean_time_in_system:.2f}")
"""