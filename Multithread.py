# -*- coding: utf-8 -*-
"""
Created on Tue Feb  8 16:43:50 2022

@author: baubergeon
"""

import numpy as np
import pandas as pd
import math
import logging
import threading
import time
import matplotlib.pyplot as plt

import pickle


def distance2(lat1,lon1,lat2,lon2):
    """
    Calculate the Haversine distance.

    Parameters
    ----------
    lat1 : float
        latitude of the original point
    lon1 : float
        longitude of the original point
    lat2 : float
        latitude of the point of destination
    lon2 : float
        longitude of the point of destination
    Returns
    -------
    distance_in_km : float
    """
    radius = 6371  # km

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) * math.sin(dlat / 2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) * math.sin(dlon / 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    d = radius * c

    return d

def CalculDistance_thread(df_orig : pd.DataFrame,df_dest : pd.DataFrame, results: list):
    """
    Function launched on an unique processor

    Parameters
    ----------
    df_orig : DataFrame
        DataFrame containing at least columns 'latitude' and 'longitude'
    df_dest : DataFrame
        DataFrame containing at least columns 'latitude' and 'longitude'
    results :list
        List of results in which every process append their own result
    Returns
        Nothing. The return of  the function  is save in the argument "result"
    -------
    """
    res=pd.DataFrame(index=df_orig.index,columns=df_dest.index)
    start=time.time()
    for i in res.index:
        lat1=df_orig.loc[i,'latitude']
        lon1=df_orig.loc[i,'longitude']
        for j in res.columns:
            lat2=df_dest.loc[j,'latitude']
            lon2=df_dest.loc[j,'longitude']
            res.loc[i,j]=distance2(lat1,lon1,lat2,lon2)
    Letime=time.time()-start
    results.append(np.array([res,Letime,time.time()]))

def Distance_MultiThread(df_origin :pd.DataFrame, df_destination :pd.DataFrame, nThreads =2):
    """
    Function which splits the data and organize the processor according to the number nProc

    Parameters
    ----------
    df_orig : DataFrame
        DataFrame containing at least columns 'latitude' and 'longitude'
    df_dest : DataFrame
        DataFrame containing at least columns 'latitude' and 'longitude'
    nThreads :int
        Number of  threads used
            
    Returns
    array df_final
        (df_final : DataFrame, exec_time: list)
    -------
    """

    N = df_origin.shape[0]
    exec_time=0
    com_time=0
    index_a = [N // nThreads * i for i in range(nThreads)]
    index_b = [N // nThreads * (i + 1) for i in range(nThreads)]
    results = list()
    
    if N % nThreads != 0:
        index_b[-1]=N
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")

    threads=list()
    start = time.time()
    launch_time=[]  #Moment où le thread est lancé:
    for p in range(nThreads):
        logging.info("Main    : create and start thread %d.", p)
        x=threading.Thread(target=CalculDistance_thread,
                        args=(df_origin.iloc[index_a[p]:index_b[p], :], df_destination, results))
        launch_time.append(time.time())
        threads.append(x)
        x.start()
    for p, thread in enumerate(threads):
        logging.info("Main    : before joining thread %d.", p)
        thread.join()
        logging.info("Main    : thread %d done", p)
    
    exec_time = time.time()- start
    #récupération du temps total des threads : time fin de calcul  - time de création
    #Attention pas vraiment exacte, le 5ème threads lancé n'est pas nécessairement le 5ème qui a finit.
    #Variable utilisée pour essayer  de comprendre le  gil.
    for i in range(len(results)):
        launch_time[i]=results[i][2]-launch_time[i]

    df_final = pd.DataFrame(results[0][0])
    exec_time_threads = [results[0][1]]
    for r in range(1,len(results)):
        df_final=pd.concat([df_final,results[r][0]])
        exec_time_threads.append(results[r][1])
    df_final.sort_index(inplace=True)
    com_time = time.time() - start - exec_time
    return np.array([df_final, exec_time_threads, exec_time, com_time,launch_time], dtype=object)
    



                    
def extract_coord(geostring : str):
    where=geostring.find(',')
    return[float(geostring[:where]),float(geostring[where+1:])]

if __name__=='__main__':
    path_paul = 'C:/Users/petit/OneDrive/Bureau/Paul/MS/S1/elements logiciels/Elements_Logiciels_ENSAE-main/Elements_Logiciels_ENSAE-main/'
    path_thomas_beline =''

    #Changement de chemin  en fonction:
    path=path_thomas_beline
    data = pd.read_csv(path+'annonces_immo.csv')
    data = data[['approximate_latitude', 'approximate_longitude']]
    data.columns = ['latitude', 'longitude']

    df_gare = pd.read_csv(path+'referentiel-gares-voyageurs.csv', sep=';')
    # Suppression des 11 gares sans coordonnéées GPS
    df_gare = df_gare[df_gare['WGS 84'].isnull() == False]

    gareratp = pd.read_csv(path+'emplacement-des-gares-idf.csv', sep=';')
    gareratp["latitude"] = gareratp.apply(
        lambda x: extract_coord(x['Geo Point'])[0],
        axis=1)
    gareratp["longitude"] = gareratp.apply(
        lambda x: extract_coord(x['Geo Point'])[1],
        axis=1)

    df_gare2 = df_gare[['Latitude', 'Longitude', 'WGS 84']]
    gareratp2 = gareratp[['latitude', 'longitude', 'Geo Point']]
    df_gare2.columns = gareratp2.columns

    # concatenation des DataFrame SNCF & RATP
    df_train = pd.concat([df_gare2, gareratp2], ignore_index=True)
    df_train.drop_duplicates(inplace=True)  # Suppresion des gares en doublon en IDF

    elem_max=500
    df_orig = data[:elem_max].copy()
    
    elem_max2=df_train.shape[0]

    df_dest = df_train[:elem_max2].copy()

    nb_threads=np.logspace(0,5,6, base=2)
    nb_threads=np.logspace(0,3,4, base=2)
    time_threads=[]
    time_exec=[]
    time_com=[]
    time_creation_to_exec=[]
    for nb_thread in nb_threads:
        print("Multiprocess starting for {} Threads".format(int(nb_thread)))
        t=time.time()
        res = Distance_MultiThread(df_orig, df_dest, nThreads = int(nb_thread))
        pd.DataFrame(res[0].transpose().min()).to_excel('Res_Thread/MultiThread_N_'+str(nb_thread)+'.xlsx')
        time_threads.append(res[1])
        time_exec.append(res[2])
        time_com.append(res[3])
        time_creation_to_exec.append(res[4])
        t2=time.time()-t
        del res #Libérer de la mémoire
        print("Temps d'éxécution pour gares (Threads {}: {} secondes".format(int(nb_thread),round(t2, 2)))


    
    c=2
    if len(time_creation_to_exec)%2==0:
        l=len(time_creation_to_exec)//2
    else:
        l=len(time_creation_to_exec)//2+1

    fig=plt.figure(figsize=(10,10))
    for i in range(len(time_creation_to_exec)):
        sub_arg=int(str(l)+str(c)+str(i+1))
        plt.subplot(sub_arg)
        plt.bar(range(1,int(nb_threads[i])+1),time_creation_to_exec[i],fill=False)
        plt.plot(range(1,int(nb_threads[i])+1),time_threads[i],'m--',label='temps  exec')
        plt.title('Temps execution par thread pour {}  threads'.format(int(nb_threads[i])))
        plt.xlabel('threads')
        if nb_threads[i]<20:
            plt.xticks(range(1,int(nb_threads[i])+1))
        plt.ylabel('time (s)')
    fig.tight_layout()
    plt.savefig('time_per_thread.jpg',dpi=300)
    plt.show()

    
    time_com=[]
    for i in range(len(time_threads)):
        max_time_process=np.max(time_threads[i])
        time_com.append(time_exec[i]-max_time_process)
        
        
        
        
    plt.plot(nb_threads,time_exec,label='Temps total éxécution')
    plt.ylabel('time (s) - Execution')
    plt.title('Temps en fonction du nombre de thread')  
    plt.xlabel('threads')
    plt.legend()
    plt.savefig('Threads_time.jpg',dpi=300)
    plt.show()
     
    fig, ax1=plt.subplots()
    plt.plot(nb_threads,time_exec,label='Temps total éxécution')
    plt.ylabel('time (s) - Execution')
    plt.title('Temps en fonction du nombre de thread')
    plt.legend(loc='best')
    ax2=ax1.twinx()
    plt.plot(nb_threads,time_com,'m--',label='Temps de communication')
    plt.xlabel('threads')
    plt.ylabel('time (s) - Communication')
    plt.legend(loc='best')
    plt.savefig('Threads_total_time.jpg',dpi=300)
    plt.show()
    
    

print('Fin')
    
    
    
