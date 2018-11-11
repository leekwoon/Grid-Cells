import numpy as np
import os 
import matplotlib.pyplot as plt
import os
from scipy.signal import correlate2d

from ratSimulator import RatSimulator
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

def showGridCells(agent, dataGenerator, num_traj, num_steps, pcu, hcu, llu, bins, place_cell_centers, head_cell_centers):
    factor=2.2/bins
    activityMap=np.zeros((llu, bins, bins))
    counterActivityMap=np.zeros((llu, bins, bins))

    X=np.zeros((num_traj,num_steps,3))
    positions=np.zeros((num_traj,num_steps,2))
    angles=np.zeros((num_traj,num_steps,1))

    env=RatSimulator(num_steps)

    print(">>Generating trajectory")
    for i in range(num_traj):
        vel, angVel, pos, angle =env.generateTrajectory()
        X[i,:,0]=vel
        X[i,:,1]=np.sin(angVel)
        X[i,:,2]=np.cos(angVel)
        positions[i,:]=pos

    init_X=np.zeros((num_traj,pcu + hcu))
    init_X[:, :pcu]=dataGenerator.computePlaceCellsDistrib(positions[:,0], place_cell_centers)
    init_X[:, pcu:]=dataGenerator.computeHeadCellsDistrib(angles[:,0], head_cell_centers)


    print(">>Computing Actvity maps")
    #Feed 500 examples at time to avoid memory problems. Otherwise (10000*100=1million matrix)
    batch_size=500
    for startB in range(0, num_traj, batch_size):
        endB=startB+batch_size

        #Store the LSTM_state at each timestep. Use these instead of initialize new ones 
        #except at timestep=0
        hidden_state=np.zeros((batch_size, 128))
        cell_state=np.zeros((batch_size, 128))

        #Divide the sequence in 100 steps.
        for startT in range(0, num_steps, 100):
            endT=startT+100

            #Retrieve the inputs for the timestep
            xBatch=X[startB:endB, startT:endT]

            #When the timestep=0, initialize the hidden and cell state of LSTm using init_X. if not timestep=0, the network will use cell_state and hidden_state
            feed_dict={ agent.X: xBatch, 
                        agent.placeCellGround: init_X[startB:endB, :pcu], 
                        agent.headCellGround: init_X[startB:endB, pcu:],
                        agent.timestep: startT,
                        agent.old_cell_state: cell_state,
                        agent.old_hidden_state: hidden_state}
            
            lstm_state, linearNeurons=agent.sess.run([agent.hidden_cell_statesTuple, agent.linearLayer], feed_dict=feed_dict)
            
            #We want that for the next timestep training the hidden state and cell state of the LSTM cells 
            #have the same values of the h_state and c_state oututed at the previous timestep training
            hidden_state=lstm_state[0]
            cell_state=lstm_state[1]

            #Convert 500,100,2 -> 50000,2
            posReshaped=np.reshape(positions[startB:endB,startT:endT],(-1,2))

            #save the value of the neurons in the linear layer at each timestep
            for t in range(linearNeurons.shape[0]):
                #Compute which bins are for each position
                bin_x, bin_y=(posReshaped[t]//factor).astype(int)

                if(bin_y==bins):
                    bin_y=bins-1
                elif(bin_x==bins):
                    bin_x=bins-1

                #Now there are the 512 values of the same location
                activityMap[:,bin_y, bin_x]+=np.abs(linearNeurons[t])#linearNeurons must be a vector of 512
                counterActivityMap[:, bin_y, bin_x]+=np.ones((512))

    counterActivityMap[counterActivityMap==0]=1
    #Compute average value
    result=activityMap/counterActivityMap

    os.makedirs("activityMaps", exist_ok=True)
    os.makedirs("corrMaps", exist_ok=True)

    '''
    I want to show 64 neurons in each image so 8x8
    it means that there will be 8 images
    '''

    cols=8

    #Save images
    fig=plt.figure(figsize=(80,80))
    #For each unit in the linear layer
    for i in range(llu):
        plt.subplot(llu//cols, cols, i+1)
        plt.axis('off')
        plt.title("Neuron "+str(i+1))
        #Normalize activity map
        normMap=(result[i]-np.min(result[i]))/(np.max(result[i])-np.min(result[i]))
        plt.imshow(normMap, cmap="jet", origin="lower")

    fig.savefig('activityMaps/neurons.jpg')

    for i in range(llu):
        plt.subplot(llu//cols, cols, i+1)
        plt.axis('off')
        plt.title("Neuron "+str(i+1))
        #Normalize activity map
        normMap=(result[i]-np.min(result[i]))/(np.max(result[i])-np.min(result[i]))
        plt.imshow(correlate2d(normMap, normMap), cmap="jet", origin="lower")

    fig.savefig('corrMaps/neurons.jpg')






