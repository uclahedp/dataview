import sys
import os
from pathlib import Path as pathlibPath

#Used for sci notation spinbox
import re

import h5py

import numpy as np


from PyQt5 import QtWidgets, QtGui

import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.figure
import matplotlib.cm





class ApplicationWindow(QtWidgets.QMainWindow):
     
    def __init__(self):
        super().__init__()
        self.debug = True
        self.buildGUI()


    def buildGUI(self):
        self._main = QtWidgets.QWidget()
        self.setCentralWidget(self._main)
        
        #Playing around with a custom style sheet...
        #self.setStyleSheet(open('stylesheet.css').read())
        
        self.setWindowTitle("HEDP dataView")
        
        #hdf5 filepath
        self.filepath = ''
    
        #Array of axes dictionaries
        self.axes = []
        
        #Currently selected axes, defaults to 0 for both
        #Second element is only used for 2D plots
        self.cur_axes = [0,0]
      
        #Used to smoothly transfer axes info when new files loaded  
        self.last_cur_axes = [0,0]
        self.last_axes = []
        
        #Data range (y values for 1D or z values for 2D)
        self.datarange = [None, None]

        #Semi-arbitrarily chosen subset of the mathplotlib colorsmaps to include
        self.colormap_dict = {'Autumn':'autumn', "Winter":"winter", "Cool":"cool", 
                          "Ocean":"ocean", "Rainbow":"gist_rainbow",
                          "Seismic":"seismic", "RedGrey":"RdGy",
                          "Coolwarm":"coolwarm"}
        
        #Many GUI elements are connected to function calls
        #By default, Pyqt5 will trigger these functions sometimes when we don't
        #want it to. Elements added to this list will be temporarily
        #disconnected at such times.
        self.connectedList = []
       
        

        #This is the primary layout
        self.layout = QtWidgets.QHBoxLayout(self._main)
        
        #
        #Define Actions
        #
        quitAct = QtWidgets.QAction(" &Quit", self)
        quitAct.triggered.connect(self.close)
        
        loadAct = QtWidgets.QAction(" &Load", self)
        loadAct.triggered.connect(self.fileDialog)
        
        savePlotAct = QtWidgets.QAction(" &Save Plot", self)
        savePlotAct.triggered.connect(self.savePlot)
        
        
        #SETUP MENU
        menubar = self.menuBar()
        #Necessary for OSX, which trys to put menu bar on the top of the screen
        menubar.setNativeMenuBar(False) 
        menubar.addAction(quitAct)
        menubar.addAction(loadAct)
        menubar.addAction(savePlotAct)
        

        self.centerbox = QtWidgets.QVBoxLayout()
        self.layout.addLayout(self.centerbox)
        
        self.rightbox = QtWidgets.QVBoxLayout()
        self.layout.addLayout(self.rightbox)
        
        self.select_ax_box = QtWidgets.QVBoxLayout()
        self.rightbox.addLayout(self.select_ax_box)
        
        #Make divider line
        divFrame = QtWidgets.QFrame()
        divFrame.setFrameShape(QtWidgets.QFrame.HLine)
        self.rightbox.addWidget(divFrame)
        
        self.axesbox = QtWidgets.QVBoxLayout()
        self.rightbox.addLayout(self.axesbox)
        
        
        #Create the plot-type dropdown box
        self.plottype_box = QtWidgets.QHBoxLayout()
        self.centerbox.addLayout(self.plottype_box)
        
        self.plottype_label = QtWidgets.QLabel("Plot Type: ")
        self.plottype_box.addWidget(self.plottype_label)
        
        self.plottype_field = QtWidgets.QComboBox()
        self.plottype_field.addItem('1D')
        self.plottype_field.addItem('2D')
        self.plottype_field.show()
        self.plottype_box.addWidget(self.plottype_field)
        self.plottype_field.currentIndexChanged.connect(self.updatePlotTypeAction)
        self.connectedList.append(self.plottype_field)
        
        self.plot_title_checkbox = QtWidgets.QCheckBox("Auto plot title?")
        self.plot_title_checkbox.setChecked(True)  
        self.plottype_box.addWidget(self.plot_title_checkbox)
        self.plot_title_checkbox.stateChanged.connect(self.makePlot)
        self.connectedList.append(self.plot_title_checkbox)
        
        
        self.fig_2d_props_box = QtWidgets.QHBoxLayout()
        self.centerbox.addLayout(self.fig_2d_props_box)
        
        self.fig_2d_label = QtWidgets.QLabel("2D Plot Parameters: ")
        self.fig_2d_props_box.addWidget(self.fig_2d_label)
        
        self.plotImageBtn = QtWidgets.QRadioButton("ImagePlot")
        self.plotImageBtn.setChecked(True)
        self.fig_2d_props_box.addWidget(self.plotImageBtn)
        self.plotImageBtn.toggled.connect(self.makePlot)
        
        self.plotContourBtn = QtWidgets.QRadioButton("ContourPlot")
        self.fig_2d_props_box.addWidget(self.plotContourBtn)
        
        #Make colormap selection bar
        self.colormap_lbl = QtWidgets.QLabel("Colormap: ")
        self.fig_2d_props_box.addWidget(self.colormap_lbl)
        self.colormap_field = QtWidgets.QComboBox()
        self.fig_2d_props_box.addWidget(self.colormap_field)
        for k in self.colormap_dict.keys():
            self.colormap_field.addItem(k)
        self.colormap_field.currentIndexChanged.connect(self.makePlot)
        self.connectedList.append(self.colormap_field)

        #This label shows warnings to explain why plots weren't made
        self.warninglabel = QtWidgets.QLabel('')
        self.centerbox.addWidget(self.warninglabel)
        
        #Create the figure that plots will be made into
        self.figure = matplotlib.figure.Figure(figsize=(5, 3))
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumSize(500, 500)
        self.centerbox.addWidget(self.canvas)
        
        
        #Create the datarange box
        self.datarange_box = QtWidgets.QHBoxLayout()
        self.centerbox.addLayout(self.datarange_box)
  
        
        self.datarange_auto = QtWidgets.QCheckBox("Autorange?")
        self.datarange_auto.setChecked(True)  
        self.datarange_box.addWidget(self.datarange_auto)
        self.datarange_auto.stateChanged.connect(self.makePlot)

        
        self.datarange_lbl = QtWidgets.QLabel("Data Range: ")
        self.datarange_box.addWidget(self.datarange_lbl)
        
        self.datarange_a = ScientificDoubleSpinBox()
        self.datarange_a.setRange(-1e100, 1e100)
        self.datarange_box.addWidget(self.datarange_a )
        self.datarange_a.editingFinished.connect(self.makePlot)
        self.connectedList.append(self.datarange_a)
        
        self.datarange_b = ScientificDoubleSpinBox()
        self.datarange_b.setRange(-1e100, 1e100)
        self.datarange_box.addWidget(self.datarange_b )
        self.datarange_b.editingFinished.connect(self.makePlot)
        self.connectedList.append(self.datarange_b)
        
        self.datarange_unitlbl = QtWidgets.QLabel("")
        self.datarange_box.addWidget(self.datarange_unitlbl)


        
        #Create the first axis dropdown menu
        self.dropdown1_box = QtWidgets.QHBoxLayout()
        self.select_ax_box.addLayout(self.dropdown1_box)
        
        self.dropdown1_label = QtWidgets.QLabel("Axis 1: ")
        self.dropdown1_box.addWidget(self.dropdown1_label)
        
        self.dropdown1 = QtWidgets.QComboBox()
        self.dropdown1_box.addWidget(self.dropdown1)
        self.dropdown1.currentIndexChanged.connect(self.updateAxesFieldsAction)
        self.connectedList.append(self.dropdown1)
        
        #Create the second axis dropdown menu
        self.dropdown2_box = QtWidgets.QHBoxLayout()
        self.select_ax_box.addLayout(self.dropdown2_box)
        
        self.dropdown2_label = QtWidgets.QLabel("Axis 2: ")
        self.dropdown2_box.addWidget(self.dropdown2_label)
        
        self.dropdown2 = QtWidgets.QComboBox()
        self.dropdown2_box.addWidget(self.dropdown2)
        self.dropdown2.currentIndexChanged.connect(self.updateAxesFieldsAction)
        self.connectedList.append(self.dropdown2)

        
        
    def freezeGUI(self):
         if self.debug:
             print("Freezing GUI elements")
         for elm in self.connectedList:
              elm.blockSignals(True)
    def unfreezeGUI(self):
        if self.debug:
             print("Unfreezing GUI elements")
        for elm in self.connectedList:
              elm.blockSignals(False)
        

    def fileDialog(self):
        if self.debug:
             print("Beginning file dialog")
        opendialog = QtWidgets.QFileDialog()
        opendialog.setNameFilter("HDF5 Files (*.hf5, *.h5)")
        userinput = pathlibPath( opendialog.getOpenFileName(self, "Select file to open", "", "hdf5 Files (*.hdf5)")[0] )
        
        if not userinput.is_file():
             print("Invalid input (ignoring): " + str(userinput) )
                
        else:
             print("Loading file: " + str(userinput) )
             self.filepath = userinput
             
             #Saving old settings and resetting arrays to default
             self.last_axes = self.axes #Copy over any axes to memory
             self.axes = []
             self.last_cur_axes = self.cur_axes
             self.cur_axes = (0,)
             
             with h5py.File(self.filepath, 'r') as f:
                  temp_axes = ( f['data'].attrs['dimensions'] ) 
                  dataunit = f['data'].attrs['unit']
                  self.datarange_unitlbl.setText(dataunit)
                  
                  for ind, ax in enumerate(temp_axes):
                     ax_dict = {}
                     name = ax.decode("utf-8")
                     ax_dict['name'] =  name
                     ax_dict['ax'] = f[name][:]
                     ax_dict['axind'] = ind
                     ax_dict['unit'] = f[name].attrs['unit']
                     
                     ax_dict['indminmax'] = ( 0 ,  len(f[name]) -1 )
                     #ax_dict['indrange'] = ax_dict['indminmax']
                     ax_dict['valminmax'] = ( f[name][0] , f[name][-1] )
                     #ax_dict['valrange'] = ax_dict['valminmax'] 
                     
                     try:
                         ax_dict['step'] = np.mean(np.gradient(ax_dict['ax']))
                     except ValueError:
                         ax_dict['step'] = 1
                         
                     self.axes.append(ax_dict)
                    
             self.freezeGUI()
             self.initAxesBoxes()
             self.unfreezeGUI()


    def initAxesBoxes(self):
        if self.debug:
             print("Initializing Axes Boxes")
        #Remove old widgets
        self.clearLayout(self.axesbox)
        
        
        #Remove old items from dropdown menus
        self.dropdown1.clear()
        self.dropdown2.clear()

        for i, ax in enumerate(self.axes):
            #Take the ax_dict out of the axes array
            ax_dict = self.axes[i]
            
            #Add the axes names to the dropdown menus
            self.dropdown1.addItem(ax_dict['name'])
            self.dropdown2.addItem(ax_dict['name'])

            ax_dict['box'] = QtWidgets.QHBoxLayout()
            self.axesbox.addLayout(ax_dict['box'])
  

            ax_dict['label1']  = QtWidgets.QLabel('')  
            ax_dict['label1'].setFixedWidth(160)
            ax_dict['box'].addWidget(ax_dict['label1'])
            
            ax_dict['indvalbtngrp'] = QtWidgets.QButtonGroup()
            
            ax_dict['valbtn'] = QtWidgets.QRadioButton("Val")
            ax_dict['valbtn'].setChecked(True)
            ax_dict['box'].addWidget(ax_dict['valbtn'])
            ax_dict['indvalbtngrp'].addButton(ax_dict['valbtn'])
            ax_dict['valbtn'].toggled.connect(self.updateIndValToggleAction)
                 
            ax_dict['indbtn'] = QtWidgets.QRadioButton("Ind")
            ax_dict['indbtn'].setChecked(False)
            ax_dict['indvalbtngrp'].addButton(ax_dict['indbtn'])
            ax_dict['box'].addWidget(ax_dict['indbtn'])
            ax_dict['indbtn'].toggled.connect(self.updateIndValToggleAction)
            

            width = 80
            ax_dict['ind_a']  = ScientificDoubleSpinBox()
            ax_dict['ind_a'].setRange(ax_dict['indminmax'][0], ax_dict['indminmax'][1])
            ax_dict['ind_a'].setSingleStep(1)
            ax_dict['ind_a'].setFixedWidth(width)
            ax_dict['ind_a'].setValue(0)
            ax_dict['ind_a'].setWrapping(True)
            ax_dict['box'].addWidget(ax_dict['ind_a'])
            ax_dict['ind_a'].editingFinished.connect(self.updateAxesFieldsAction)
            
            ax_dict['val_a']  = ScientificDoubleSpinBox()
            ax_dict['val_a'].setRange(ax_dict['valminmax'][0], ax_dict['valminmax'][1])
            #ax_dict['val_a'].setSingleStep(ax_dict['step'])
            ax_dict['val_a'].setFixedWidth(width)
            ax_dict['val_a'].setValue(0)
            ax_dict['val_a'].setWrapping(True)
            ax_dict['box'].addWidget(ax_dict['val_a'])
            ax_dict['val_a'].editingFinished.connect(self.updateAxesFieldsAction)
            
            
            ax_dict['ind_b']  = ScientificDoubleSpinBox()
            ax_dict['ind_b'].setRange(ax_dict['indminmax'][0], ax_dict['indminmax'][1])
            ax_dict['ind_b'].setSingleStep(1)
            ax_dict['ind_b'].setFixedWidth(width)
            ax_dict['ind_b'].setValue(ax_dict['indminmax'][1])
            ax_dict['ind_b'].setWrapping(True)
            ax_dict['box'].addWidget(ax_dict['ind_b'])
            ax_dict['ind_b'].editingFinished.connect(self.updateAxesFieldsAction)
            
            ax_dict['val_b']  = ScientificDoubleSpinBox()
            ax_dict['val_b'].setRange(ax_dict['valminmax'][0], ax_dict['valminmax'][1])
            #ax_dict['val_b'].setSingleStep(ax_dict['step'])
            ax_dict['val_b'].setFixedWidth(width)
            ax_dict['val_b'].setValue(ax_dict['valminmax'][1])
            ax_dict['val_b'].setWrapping(True)
            ax_dict['box'].addWidget(ax_dict['val_b'])
            ax_dict['val_b'].editingFinished.connect(self.updateAxesFieldsAction)
            
            
            ax_dict['avgcheckbox'] = QtWidgets.QCheckBox("Avg")
            ax_dict['avgcheckbox'].setChecked(False)  
            ax_dict['box'].addWidget(ax_dict['avgcheckbox'])
            ax_dict['avgcheckbox'].stateChanged.connect(self.updateAvgCheckBoxAction)
            
            #Put the ax_dict back into the axes array
            self.axes[i] = ax_dict
        
        #If names of any old axes match those of any new axes
        #attempt to copy over the currently chosen indices
        for i, ax in enumerate(self.axes):
            for j, old_ax in enumerate(self.last_axes):
                if ax['name'] == old_ax['name']:
                    ax['ind_a'].setValue( old_ax['ind_a'].value() )
                    ax['ind_b'].setValue( old_ax['ind_b'].value() )
                    ax['val_a'].setValue( old_ax['val_a'].value() )
                    ax['val_b'].setValue( old_ax['val_b'].value() )
    
 
        #If new axes match old ones, set the cur_axes to match
        if len(self.last_axes) != 0:
            cur_name = self.last_axes[ self.last_cur_axes[0] ]['name']
            ind = self.dropdown1.findText(cur_name)
            if ind != -1:
                self.dropdown1.setCurrentIndex(ind)
                
            cur_name = self.last_axes[ self.last_cur_axes[1] ]['name']
            ind = self.dropdown2.findText(cur_name)
            if ind != -1:
                self.dropdown2.setCurrentIndex(ind)
                
        #Once all the fields have been created, make sure they are set correctly
        self.updateAxesFields()


    def updateAxesFields(self):
       if self.debug:
           print("Updating Axes Fields and Check Boxes")
       #Update based on how the plottype is set currently
       if self.plottype_field.currentIndex() == 0:
           self.cur_axes = (self.dropdown1.currentIndex(), )
           self.dropdown2_label.hide()
           self.dropdown2.hide()
       elif self.plottype_field.currentIndex() == 1:
           self.cur_axes = (self.dropdown1.currentIndex(), self.dropdown2.currentIndex())
           self.dropdown2_label.show()
           self.dropdown2.show()
           
       #Update each of the axes fields visibility based on field settings
       for i, ax in enumerate(self.axes):
           #Enable/Disable fields as appropriate
           #a is disabled only if the avg box is checked
           is_avg = ax['avgcheckbox'].isChecked()
           ax['ind_a'].setDisabled(is_avg)
           ax['val_a'].setDisabled(is_avg)
           #b is only enabled when it is the current axis AND not averaged
           if i in self.cur_axes and ax['avgcheckbox'].isChecked()==False :
               ax['ind_b'].setDisabled(False)
               ax['val_b'].setDisabled(False)
           else:
               ax['ind_b'].setDisabled(True)
               ax['val_b'].setDisabled(True) 
               
           #Hide or show fields based on index/value mode
           if ax['valbtn'].isChecked():
                ax['ind_a'].hide()
                ax['ind_b'].hide()
                ax['val_a'].show()
                ax['val_b'].show()
           elif ax['indbtn'].isChecked():
                ax['val_a'].hide()
                ax['val_b'].hide()
                ax['ind_a'].show()
                ax['ind_b'].show()

                
               
           #Calculate the indices or values...
           #whichever we aren't controlling right now
           if ax['valbtn'].isChecked():
                val_a = float(ax['val_a'].value())
                val_b = float(ax['val_b'].value())
                ind_a = np.argmin(np.abs(ax['ax'] - val_a ))
                ind_b = np.argmin(np.abs(ax['ax'] - val_b ))
                ax['ind_a'].setValue(ind_a)
                ax['ind_b'].setValue(ind_b)

           elif ax['indbtn'].isChecked():
                ind_a = int(ax['ind_a'].value())
                ind_b = int(ax['ind_b'].value())
                val_a = ax['ax'][ind_a]
                val_b = ax['ax'][ind_b]
                ax['val_a'].setValue(val_a)
                ax['val_b'].setValue(val_b)
                
               
           #Update the label for each line
           if ax['valbtn'].isChecked():
               #Currently using values, format label to match
               lbltxt = ( ax['name'] + ': ' +
                         'Values [' + self.numFormat(ax['valminmax'][0]) +
                         ', ' + self.numFormat(ax['valminmax'][1]) +
                         '] ' + ax['unit'])
           else:
                #Currently using indices, format label to match
                lbltxt = ( ax['name'] + ': ' + 
                          'Indices [' + self.numFormat(ax['indminmax'][0]) +
                          ', ' + self.numFormat(ax['indminmax'][1]) +
                          ']')
           ax['label1'].setText(lbltxt)
          
    #ACTION FUNTIONS (tied to buttons/fields/etc.)
    
    def updateAxesFieldsAction(self):
        if self.debug:
           print("Triggered updateAxesFieldsAction")
        self.updateAxesFields()
        self.makePlot()
    
    def updatePlotTypeAction(self):
        if self.debug:
             print("Triggered updatePlotTypeActio")
        self.updateAxesFields()
        self.makePlot()

    def updateAvgCheckBoxAction(self):
        if self.debug:
           print("Triggered updateAvgCheckBoxAction")
        self.updateAxesFields()
        self.makePlot()
        
        
    def updateIndValToggleAction(self):
         if self.debug:
           print("Triggered updateIndValToggle")
         self.updateAxesFields()
         self.makePlot()


    def validateChoices(self):
       #Make a temporary array of the axes that are ACTUALLY about to be
       #plotted (ignoring 2nd one if the plot is 2D)
       if self.plottype_field.currentIndex() == 0:
            thisplot_axes = [self.axes[0]]
       elif self.plottype_field.currentIndex() == 1:
            thisplot_axes = self.axes
      
         
       #Validate file
       if not os.path.isfile(self.filepath):
           self.warninglabel.setText("WARNING: Invalid filepath!")
           return False
       elif os.path.splitext(self.filepath)[-1] != '.hdf5':
           self.warninglabel.setText("WARNING: Filepath must end in .hdf5!")
           return False
      
       #Validate plot params
       #Selected axes should be different
       if  self.plottype_field.currentIndex() == 1 and self.dropdown1.currentIndex() == self.dropdown2.currentIndex():
           self.warninglabel.setText("WARNING: Axes selected need to be different!")
           return False
      
       #Current axes should be larger than 1D
       for axind in self.cur_axes:
           ax = self.axes[axind]
           #Check that the original axis is is > 1 long
           l = ax['ax'].shape[0]
           print(l)
           if l > 1:
               pass
           else:
               self.warninglabel.setText("WARNING: Axis must have length > 1: " + str(ax['name']))
               return False
          #Check to make sure it hasn't been TRIMMED to be < 2
          
       

       #Check to make sure the axes make sense
       for ind, ax_dict in enumerate(self.axes):
           if ind in thisplot_axes:
               if ax_dict['ind_a'].text()  == ax_dict['ind_b'].text():
                   self.warninglabel.setText("WARNING: Axes range is 0!")
                   return False
               elif float(ax_dict['ind_a'].text())  > float(ax_dict['ind_b'].text()):
                   self.warninglabel.setText("WARNING: First range element should be smallest!")
                   return False
              
       #If no warnings are found, set the label to blank and return True
       self.warninglabel.setText("")
       return True
    
    


    def makePlot(self):
        self.clearCanvas()
        if self.validateChoices():
            if self.plottype_field.currentIndex() == 0:
                self.plot1D()
            elif self.plottype_field.currentIndex() == 1:
                self.plot2D()

            
            
            
    def clearCanvas(self):
        try:
            self.figure.clf()
            self.canvas_ax.clear()
            self.canvas.draw()
        except AttributeError as e:
            pass
        
    def clearLayout(self, layout):
        if layout !=None:
            while layout.count():
                child = layout.takeAt(0)
                if child.widget() is not None:
                    child.widget().deleteLater()
                elif child.layout() is not None:
                    self.clearLayout(child.layout())
        
        

    def plot1D(self):
        
        #Horizontal axis for this 1D plot - obj
        ax_ind = self.cur_axes[0]
        avg_axes = []
        dslice = []
        

        for i in range(len(self.axes) ):
            d  = self.axes[i]
            if i == ax_ind:   
                hname = d['name']
                a = int(d['ind_a'].value())
                b = int(d['ind_b'].value())
                dslice.append( slice(a, b, 1) )
                hslice = slice(a,b, 1)
                
            elif d['avgcheckbox'].isChecked():
                dslice.append( slice(None,None,None) )
                avg_axes.append(i)

            else:
                a = int(d['ind_a'].text())
                dslice.append( slice(a, a+1, 1) )
                
        with h5py.File(self.filepath, 'r') as f:
            hax = np.squeeze(f[hname][hslice])#already a tuple
            hunit = str(f[hname].attrs['unit'])
            
            data = f['data'][tuple(dslice)]
            if len(avg_axes) != 0:
                data = np.mean(data, axis=tuple(avg_axes ))
            data = np.squeeze(data)
            dataunit  = str(f['data'].attrs['unit'])
            

        self.canvas_ax = self.canvas.figure.subplots()


        self.canvas_ax.plot(hax, data, linestyle='-')
        
        #self.canvas_ax.text(0,1, 'THIS IS SOME SAMPLE TEXT', transform=self.canvas_ax.transAxes)
        

        self.canvas_ax.set_xlabel(str(hname) + ' (' + str(hunit) + ')')
        self.canvas_ax.set_ylabel('(' + str(dataunit) + ')')
        
        if self.plot_title_checkbox.isChecked():
            title = self.plotTitle()
            self.canvas_ax.set_title(title)

        
        #Setup axis formats
        self.canvas_ax.ticklabel_format(axis='x', scilimits=(-3,3) )
        self.canvas_ax.ticklabel_format(axis='y', scilimits=(-3,3) )
        
        #Autorange if appropriate
        if not self.datarange_auto.isChecked():
            self.canvas_ax.set_ylim(float(self.datarange_a.text()), float(self.datarange_b.text()))
            
        
            
        self.canvas.draw()
    
    def plot2D(self):
        
        #Horizontal axis for this 1D plot - obj
        hind = self.cur_axes[0]
        vind = self.cur_axes[1]
  
        dslice = []
        
        avg_axes = []
        
        for i in range(len(self.axes) ):
            d  = self.axes[i]
            if i == hind or i == vind:
                a = int(d['ind_a'].value())
                b = int(d['ind_b'].value())
                dslice.append( slice(a, b, 1) )
                
                if i == hind:
                     hname = d['name']
                     hslice = slice(a,b, 1)
                elif i == vind:
                     vname = d['name']
                     vslice = slice(a,b, 1)
            
            elif d['avgcheckbox'].isChecked():
                print(str(i) + ' is in avg_axes')
                dslice.append( slice(None,None,None) )
                avg_axes.append(i)
                
            else:
                a = int(d['ind_a'].value())
                dslice.append( slice(a, a+1, 1) )
        
        with h5py.File(self.filepath, 'r') as f:
            hax = np.squeeze(f[hname][hslice])#already a tuple
            vax = np.squeeze(f[vname][vslice])#already a tuple
            hunit = f[hname].attrs['unit']
            vunit = f[vname].attrs['unit']
            
            
            data = f['data'][tuple(dslice)]
            if len(avg_axes) != 0:
                data = np.mean(data, axis=tuple(avg_axes ))
            data = np.squeeze(data)
            dataunit  = str(f['data'].attrs['unit'])
            
            
            
            
        if vind > hind:
            data = data.transpose()
            
        
        
        if not self.datarange_auto.isChecked():
            cmin = float(self.datarange_a.text())
            cmax = float(self.datarange_b.text())
        else:
            cmin = np.min(data)
            cmax = np.max(data)
            
        levels = np.linspace(cmin, cmax, num=50)
        
        cmap_key = self.colormap_field.currentText()
        cmname = self.colormap_dict[cmap_key]
        colormap = matplotlib.cm.get_cmap(name=cmname)
        
        self.canvas_ax = self.canvas.figure.subplots()
        
        #Setup axis formats
        self.canvas_ax.ticklabel_format(axis='x', scilimits=(-3,3) )
        self.canvas_ax.ticklabel_format(axis='y', scilimits=(-3,3) )

        #Make a contour plot or image plot, depending on the selection
        if self.plotContourBtn.isChecked():
            cs = self.canvas_ax.contourf(hax, vax, data, levels, cmap=colormap)
        else:
            cs = self.canvas_ax.imshow(data, origin='lower',
                                       vmin=cmin, vmax=cmax,
                                       aspect='auto', interpolation = 'nearest',
                                       extent=[hax[0], hax[-1], vax[0], vax[-1]],
                                       cmap = colormap)
            
            
        if np.max( np.abs(data ) ) > 100 or np.max( np.abs(data ) ) < 0.01:
            cbformat = '%.1e'
        else:
            cbformat = '%.1f'
        
        
        cbar = self.canvas.figure.colorbar(cs, orientation='horizontal', 
                                           format=cbformat)
        cbar.ax.set_xlabel('(' + str(dataunit) + ')' )
        
        self.canvas_ax.set_xlabel(str(hname) + ' (' + str(hunit) + ')')
        self.canvas_ax.set_ylabel(str(vname) + ' (' + str(vunit) + ')')

        if self.plot_title_checkbox.isChecked():
            title = self.plotTitle()
            self.canvas_ax.set_title(title)
            
        
        
        
        self.canvas.draw()
        
        
    def plotTitle(self):
        strarr = []
        strarr.append( os.path.basename(self.filepath) )

        curarr = []
        otherarr = []
        
        for i, ax in enumerate(self.axes):
             axarr = ax['ax']
             
     
             a = int(ax['ind_a'].value())
             b = int(ax['ind_b'].value())
        
             if i in self.cur_axes:
                 val = ( self.numFormat(axarr[a]),
                         self.numFormat(axarr[b]),
                         ax['unit'])
                 curarr.append( ax['name'] + '=[%s,%s] %s' % val )
             elif ax['avgcheckbox'].isChecked():
                 otherarr.append( ax['name'] + '= avg' )
             else:
                 val = ( self.numFormat(axarr[a]),
                         ax['unit'])
                 otherarr.append( ax['name'] + '=%s %s' % val )
                 
        strarr.append( ', '.join(curarr) )
        strarr.append( ', '.join(otherarr))
        return '\n'.join(strarr)
                 
        
        
    def savePlot(self):
        savedialog = QtWidgets.QFileDialog()
        
        
        suggested_name = os.path.splitext(self.filepath)[0] + '.png'

        
        savefile = savedialog.getSaveFileName(self, "Save as: ", suggested_name, "")[0]
        self.figure.savefig(savefile)
        
        
    def numFormat(self, n):
        if n == int(n):
            return '%d' % n
        elif n > 100 or n < 0.01:
            return '%.2E' % n
        else:
            return '%.2f' % n
     
     
     
# This website helped with code for the scientific notation QSpinBox   
# https://jdreaver.com/posts/2014-07-28-scientific-notation-spin-box-pyside.html         
# Regular expression to find floats. Match groups are the whole string, the
# whole coefficient, the decimal part of the coefficient, and the exponent
# part.
_float_re = re.compile(r'(([+-]?\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)')

def valid_float_string(string):
    match = _float_re.search(string)
    return match.groups()[0] == string if match else False


class FloatValidator(QtGui.QValidator):

    def validate(self, string, position):
        if valid_float_string(string):
            state = QtGui.QValidator.Acceptable
        elif string == "" or string[position-1] in 'e.-+':
            state = QtGui.QValidator.Intermediate
        else:
            state = QtGui.QValidator.Invalid
        return (state, string, position)
   
    def fixup(self, text):
        match = _float_re.search(text)
        return match.groups()[0] if match else ""


class ScientificDoubleSpinBox(QtWidgets.QDoubleSpinBox):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #self.setMinimum(-np.inf)
        #self.setMaximum(np.inf)
        self.validator = FloatValidator()
        self.setDecimals(1000)

    def validate(self, text, position):
        return self.validator.validate(text, position)

    def fixup(self, text):
        return self.validator.fixup(text)

    def valueFromText(self, text):
        return float(text)

    def textFromValue(self, value):
        return format_float(value)

    def stepBy(self, steps):
        text = self.cleanText()
        groups = _float_re.search(text).groups()
        decimal = float(groups[1])
        decimal += steps
        new_string = "{:g}".format(decimal) + (groups[3] if groups[3] else "")
        self.lineEdit().setText(new_string)


def format_float(value):
    """Modified form of the 'g' format specifier."""
    string = "{:g}".format(value).replace("e+", "e")
    string = re.sub("e(-?)0*(\d+)", r"e\1\2", string)
    return string
        
        

if __name__ == "__main__":
    
    #Check if a QApplicaiton already exists, and don't open a new one if it does
    #This helps avoid kernel crashes on exit.
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)
    else:
        print('QApplication instance already exists: %s' % str(app))
    
    w = ApplicationWindow()
    w.show()
    app.exec()