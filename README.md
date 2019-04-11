# dataView
The dataView program makes 'quicklook' plots from standardized UCLAHEDP-format HDF5 files.

# Installation Instructions
Dataview requires both Python3 and some depenencies. This isn't a fancy real package yet, so you'll have to install them all manually. You can do this by either manually configuring your local python enviroment to run the package, or by installing the Anaconda distribution, which already contains most of these packages.

*Local Python Enviroment*
1) Install Python 3
2) Download the dataview.py file.
3) Install the required packages by running the following command from terminal
"pip3 install matplotlib h5py numpy PyQt5"
4) Run dataview by either clicking on the dataview.py file, or by navigating to the file in terminal and running
"python dataview.py"

*Anaconda*
1) Install Anaconda Python >= 3.6
2) (Optional): Create a new enviroment for using dataview. There shouldn't be too many conflicts with other python package requirements, but this is technically the safest way to install anything.
3) Under the "Enviroments" tab, install the following packages using the package manegar: matplotlib h5py numpy pyqt
4) Open the terminal (left click green triangle), navigate to the dataview.py file, and run
"python dataview.py". Alternately, open the file in Spyder and run it there.

Note: You can also directly install the dependencies by running the following command in the enviroment terminal:
"conda install matplotlib h5py numpy pyqt"



# Usage/Tutorial
1) Select "Load" from the toolbar and select an HDF5 file that contains a suitable dataset.
2) Select the horizontal axis (axis 1) from the dropdown menu to the right of the plot.
3) Change the range of the axes plotted by changing the indices in the fields at the bottom right. Pressing Enter will refresh the plot. The arrow keys can be used to step through indices. Changing the "Step" will change the step in which you cycle through the indices. Checking "Avg" will average over the entire dimension.
4) Autorange (bottom left) is selected by default. Select a different range and deselect this box to set your own y-axis range. 
5) To make a 2D plot, select 2D in Plot Type (top). You can now select a second axis. Note that no plot will be made if the axes are the same!
6) The colormap can be changed from a dropdown at the top. The default plot is a pixilated image, since that is what renders fastest. To see a nicer contour plot, select the "ContourPlot" button at the top.
7) Plots can be saved through a file dialog by pressing the Save Plot button on the toolbar.

You can switch to a new HDF5 file without restarting the program by pressing Load again. The program will its best to apply the settings you had on the previous file to plot the new file, so if datafiles are similar you can easily create the same plot in each one.


