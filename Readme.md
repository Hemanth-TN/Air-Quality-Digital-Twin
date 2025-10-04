This repo contains a digital twin to monitor the level of air pollutants at four cities: Bangalore, New Delhi, Chicago and Sacremento.
To view the digital twin on your machine do as follows.

* Clone this repo on your machine: run "git clone https://github.com/Hemanth-TN/Air-Quality-Digital-Twin.git"
* In your machine, navigate to the folder where you cloned this repo and run the following
     - "docker build -t dashapp . "
     - "docker run -p 8050:8050 dashapp"

You can now access the digital twin at http://localhost:8050/

The landing page is as follows

![alt text](image.png)
