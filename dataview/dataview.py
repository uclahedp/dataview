import sys
import os
from pathlib import Path as pathlibPath
import traceback

#Used for sci notation spinbox
import re

import h5py

import numpy as np

from astropy import units

from scipy import ndimage

from PyQt5 import QtWidgets, QtGui, QtCore

import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.figure
import matplotlib.cm


class ApplicationWindow(QtWidgets.QMainWindow):
     
    def __init__(self):
        super().__init__()
        self.debug = False
        self.buildGUI()


    def buildGUI(self):
        self._main = QtWidgets.QWidget()
        self.setCentralWidget(self._main)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        
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
       
        #Unit of data in file (never changes)
        self.data_native_unit = ''
        #Factor for correcting data for units
        self.data_unit_factor = 1.0
        #Storage of unit factor currently applied to data range
        self.data_cur_unit = ''#Unit displayed on data range, etc.
        
        
        
        #Plotting variables
        self.data = 0
        self.hax = {'ax': 0, 'name': '', 'slice': 0, 'unit': '', 'unit_factor': 0}
        self.vax = {'ax': 0, 'name': '', 'slice': 0, 'unit': '', 'unit_factor': 0}
        
        
        
        #DEFINE fonts
        self.text_font = QtGui.QFont()
        self.text_font.setPointSize(12)
        
        self.subtitle_font = QtGui.QFont()
        self.subtitle_font.setPointSize(16)
        self.subtitle_font.setBold(True)
        
        self.title_font = QtGui.QFont()
        self.title_font.setPointSize(22)
        self.title_font.setBold(True)
        

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
        
        #Setup options menue + actions within
        optionsMenu = QtWidgets.QMenu('Options', self)
        
        self.showAvg = QtWidgets.QAction(" &Average", self, checkable=True)
        self.showAvg.setChecked(False)
        self.showAvg.triggered.connect(self.showAvgAction)
        
        self.showFilter = QtWidgets.QAction(" &Filter", self, checkable=True)
        self.showFilter.setChecked(False)
        self.showFilter.triggered.connect(self.showFilterAction)
        
        #SETUP MENU
        menubar = self.menuBar()
        #Necessary for OSX, which trys to put menu bar on the top of the screen
        menubar.setNativeMenuBar(False) 
        
        #Add menu actions
        menubar.addAction(quitAct)
        menubar.addAction(loadAct)
        menubar.addAction(savePlotAct)
        
        #Add options menu and associated submenu options
        menubar.addMenu(optionsMenu)
        optionsMenu.addAction(self.showAvg)
        optionsMenu.addAction(self.showFilter)
        
        

        self.centerbox = QtWidgets.QVBoxLayout()
        self.layout.addLayout(self.centerbox)
        
        self.rightbox = QtWidgets.QVBoxLayout()
        self.layout.addLayout(self.rightbox)
        
        self.select_ax_box = QtWidgets.QVBoxLayout()
        self.rightbox.addLayout(self.select_ax_box)
        
        #Make divider line
        divFrame = QtWidgets.QFrame()
        divFrame.setFrameShape(QtWidgets.QFrame.HLine)
        divFrame.setLineWidth(3)
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
        self.datarange_auto.stateChanged.connect(self.updateDataRange)
        self.connectedList.append(self.datarange_auto)
        
        self.datarange_center = QtWidgets.QCheckBox("Center zero?")
        self.datarange_center.setChecked(False)  
        self.datarange_box.addWidget(self.datarange_center)
        self.datarange_center.stateChanged.connect(self.updateDataRange)
        self.connectedList.append(self.datarange_center)
        
        self.datarange_lbl = QtWidgets.QLabel("Data Range: ")
        self.datarange_lbl.setFixedWidth(80)
        self.datarange_box.addWidget(self.datarange_lbl)
        
        self.datarange_a = ScientificDoubleSpinBox()
        self.datarange_a.setRange(-1e100, 1e100)
        self.datarange_box.addWidget(self.datarange_a )
        self.datarange_a.editingFinished.connect(self.updateDataRange)
        self.connectedList.append(self.datarange_a)
        
        self.datarange_b = ScientificDoubleSpinBox()
        self.datarange_b.setRange(-1e100, 1e100)
        self.datarange_box.addWidget(self.datarange_b )
        self.datarange_b.editingFinished.connect(self.updateDataRange)
        self.connectedList.append(self.datarange_b)
        
        self.datarange_unitlbl = QtWidgets.QLabel("Data Unit: ")
        self.datarange_unitlbl.setFixedWidth(60)
        self.datarange_box.addWidget(self.datarange_unitlbl)
        
    
        self.data_unit_field = QtWidgets.QLineEdit('')
        self.data_unit_field.setFixedWidth(40)
        self.datarange_box.addWidget(self.data_unit_field)
        self.data_unit_field.editingFinished.connect(self.updateDataUnits)
        self.connectedList.append(self.data_unit_field)
        
        
        #CREATE AND FILL THE FILTER OPTIONS BOX
        self.filterbox = QtWidgets.QHBoxLayout()
        self.centerbox.addLayout(self.filterbox)
        self.filterbox_widgets = []
        
        
        self.nofilter_checkbox = QtWidgets.QRadioButton("No Filter")
        self.nofilter_checkbox.setChecked(False)  
        self.filterbox.addWidget(self.nofilter_checkbox)
        self.filterbox_widgets.append(self.nofilter_checkbox)
        self.nofilter_checkbox.toggled.connect(self.makePlot)
        
        self.lowpass_checkbox = QtWidgets.QRadioButton("Lowpass")
        self.lowpass_checkbox.setChecked(False)  
        self.filterbox.addWidget(self.lowpass_checkbox)
        self.filterbox_widgets.append(self.lowpass_checkbox)
        self.lowpass_checkbox.toggled.connect(self.makePlot)
        
        self.highpass_checkbox = QtWidgets.QRadioButton("Highpass")
        self.highpass_checkbox.setChecked(False)  
        self.filterbox.addWidget(self.highpass_checkbox)
        self.filterbox_widgets.append(self.highpass_checkbox)
        self.highpass_checkbox.toggled.connect(self.makePlot)
        

        self.filter_sigma_lbl = QtWidgets.QLabel("Filter Sigma: ")
        self.filter_sigma_lbl.setFixedWidth(100)
        self.filterbox_widgets.append(self.filter_sigma_lbl)
        self.filterbox.addWidget(self.filter_sigma_lbl)
        
        self.filter_sigma  = ScientificDoubleSpinBox()
        self.filter_sigma.setRange(0.01, 1000)
        self.filter_sigma.setSingleStep(.01)
        self.filter_sigma.setFixedWidth(80)
        self.filter_sigma.setValue(1)
        self.filter_sigma.setWrapping(False)
        self.filterbox.addWidget(self.filter_sigma)
        self.filterbox_widgets.append(self.filter_sigma)
        self.filter_sigma.editingFinished.connect(self.makePlot)
        for x in self.filterbox_widgets:
            x.hide()






        self.axis_box_label = QtWidgets.QLabel("Chose Axis/Axes")
        self.axis_box_label.setFont(self.title_font)
        self.axis_box_label.setAlignment(QtCore.Qt.AlignCenter)
        self.select_ax_box.addWidget(self.axis_box_label)
        
        
        
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
             self.cur_axes = [0,0]
             
             with h5py.File(self.filepath, 'r') as f:
                  temp_axes = ( f['data'].attrs['dimensions']  ) 
                  
                  self.data_unit_field.setText( f['data'].attrs['unit'])
                  self.data_native_unit = self.data_unit_field.text()
                  self.data_cur_unit = self.data_native_unit

                  
                  for ind, axis in enumerate(temp_axes):
                     ax = {}
                     name = axis.decode("utf-8")
                     ax['name'] =  name
                     ax['ax'] = f[name][:]
                     ax['axind'] = ind
                     ax['native_unit'] = f[name].attrs['unit']
                     
                     
                     ax['indminmax'] = ( 0 ,  len(f[name]) -1 )
                     ax['valminmax'] = ( f[name][0] , f[name][-1] )
                     
                     try:
                         ax['step'] = np.mean(np.gradient(ax['ax']))
                     except ValueError:
                         ax['step'] = 1
                         
                     self.axes.append(ax)
                    
             self.freezeGUI()
             self.initAxesBoxes()
             self.unfreezeGUI()
             self.makePlot()


    def initAxesBoxes(self):
        if self.debug:
             print("Initializing Axes Boxes")
        #Remove old widgets
        self.clearLayout(self.axesbox)
        
        #Create Controls title
        self.axis_settings_label = QtWidgets.QLabel("Axis Settings")
        self.axis_settings_label.setFont(self.title_font)
        self.axis_settings_label.setAlignment(QtCore.Qt.AlignCenter)
        self.axesbox.addWidget(self.axis_settings_label)
        
        
        #Remove old items from dropdown menus
        self.dropdown1.clear()
        self.dropdown2.clear()

        for i, ax in enumerate(self.axes):
            #Take the ax out of the axes array
            ax = self.axes[i]
            
            #Add the axes names to the dropdown menus
            self.dropdown1.addItem(ax['name'])
            self.dropdown2.addItem(ax['name'])

            #Create the top level box for this axis
            ax['box'] = QtWidgets.QVBoxLayout()
            self.axesbox.addLayout(ax['box'])
            
            #Create a list of all objects in this axis that involve real values
            #When units get changed, we can iteratively modify all of these
            #fields at once
            ax['value_list'] = []
            
            
            
            #CREATE AND FILL THE MAIN BOX
            #This box always shows
            ax['mainbox'] = QtWidgets.QHBoxLayout()
            ax['box'].addLayout(ax['mainbox'])

            ax['namelabel']  = QtWidgets.QLabel('')  
            ax['namelabel'].setFixedWidth(60)
            ax['namelabel'].setFont(self.subtitle_font)
            ax['namelabel'].setText(ax['name'] + ': ')
            ax['mainbox'].addWidget(ax['namelabel'])
            
            ax['rangelabel']  = QtWidgets.QLabel('')  
            ax['rangelabel'].setFixedWidth(200)
            ax['rangelabel'].setFont(self.text_font)
            ax['mainbox'].addWidget(ax['rangelabel'])
            
            ax['indvalbtngrp'] = QtWidgets.QButtonGroup()
            
            ax['valbtn'] = QtWidgets.QRadioButton("Val")
            ax['valbtn'].setChecked(True)
            ax['mainbox'].addWidget(ax['valbtn'])
            ax['indvalbtngrp'].addButton(ax['valbtn'])
            ax['valbtn'].toggled.connect(self.updateIndValToggleAction)
                 
            ax['indbtn'] = QtWidgets.QRadioButton("Ind")
            ax['indbtn'].setChecked(False)
            ax['indvalbtngrp'].addButton(ax['indbtn'])
            ax['mainbox'].addWidget(ax['indbtn'])
            ax['indbtn'].toggled.connect(self.updateIndValToggleAction)
            

            width = 100
            ax['ind_a']  = ScientificDoubleSpinBox()
            ax['ind_a'].setRange(ax['indminmax'][0], ax['indminmax'][1])
            ax['ind_a'].setSingleStep(1)
            ax['ind_a'].setFixedWidth(width)
            ax['ind_a'].setValue(0)
            ax['ind_a'].setWrapping(True)
            ax['mainbox'].addWidget(ax['ind_a'])
            ax['ind_a'].editingFinished.connect(self.updateAxesFieldsAction)
            
            ax['val_a']  = ScientificDoubleSpinBox()
            ax['val_a'].setRange(ax['valminmax'][0], ax['valminmax'][1])
            ax['val_a'].setFixedWidth(width)
            ax['val_a'].setValue(0)
            ax['val_a'].setWrapping(True)
            ax['mainbox'].addWidget(ax['val_a'])
            ax['value_list'].append(ax['val_a'])
            ax['val_a'].editingFinished.connect(self.updateAxesFieldsAction)
            
            
            ax['ind_b']  = ScientificDoubleSpinBox()
            ax['ind_b'].setRange(ax['indminmax'][0], ax['indminmax'][1])
            ax['ind_b'].setSingleStep(1)
            ax['ind_b'].setFixedWidth(width)
            ax['ind_b'].setValue(ax['indminmax'][1])
            ax['ind_b'].setWrapping(True)
            ax['mainbox'].addWidget(ax['ind_b'])
            ax['ind_b'].editingFinished.connect(self.updateAxesFieldsAction)
            
            ax['val_b']  = ScientificDoubleSpinBox()
            ax['val_b'].setRange(ax['valminmax'][0], ax['valminmax'][1])
            ax['val_b'].setFixedWidth(width)
            ax['val_b'].setValue(ax['valminmax'][1])
            ax['val_b'].setWrapping(True)
            ax['mainbox'].addWidget(ax['val_b'])
            ax['value_list'].append(ax['val_b'])
            ax['val_b'].editingFinished.connect(self.updateAxesFieldsAction)
            
            ax['unit_lbl'] = QtWidgets.QLabel("Unit: ")
            ax['unit_lbl'].setFixedWidth(30)
            ax['mainbox'].addWidget(ax['unit_lbl'])
        
            
            ax['unit_factor'] = 1.0
            ax['disp_unit'] = ax['native_unit']
            ax['unit_field'] = QtWidgets.QLineEdit(str(ax['native_unit']))
            ax['unit_field'].setFixedWidth(40)
            ax['mainbox'].addWidget(ax['unit_field'])
            ax['unit_field'].editingFinished.connect(lambda opt=ax : self.updateAxesUnits(opt))
            
            
            #CREATE AND FILL THE AVG OPTIONS BOX
            #This box contains averaging options
            ax['avgbox'] = QtWidgets.QHBoxLayout()
            ax['box'].addLayout(ax['avgbox'])
            ax['avgbox_widgets'] = []
            
            
            ax['avgcheckbox'] = QtWidgets.QCheckBox("Average?")
            ax['avgcheckbox'].setChecked(False)  
            ax['avgbox'].addWidget(ax['avgcheckbox'])
            ax['avgbox_widgets'].append(ax['avgcheckbox'])
            ax['avgcheckbox'].stateChanged.connect(self.updateAvgCheckBoxAction)
            

            #Make a divider line (unless this is the last axis)
            if i != len(self.axes)-1:
                ax['divFrame'] = QtWidgets.QFrame()
                ax['divFrame'].setFrameShape(QtWidgets.QFrame.HLine)
                ax['divFrame'].setLineWidth(2)
                ax['box'].addWidget(ax['divFrame'])
            
            #Put the ax back into the axes array
            self.axes[i] = ax
        
        #If names of any old axes match those of any new axes
        #attempt to copy over the currently chosen indices etc.
        for i, ax in enumerate(self.axes):
            for j, old_ax in enumerate(self.last_axes):
                if ax['name'] == old_ax['name']:
                    uf = old_ax['unit_factor']
                    ax['unit_factor'] =  uf
                    ax['disp_unit'] = old_ax['disp_unit']
                    ax['unit_field'].setText(old_ax['unit_field'].text())
                    
                    #Transfer averaging state
                    ax['avgcheckbox'].setChecked(old_ax['avgcheckbox'].isChecked())
                     
                    old_val_a = old_ax['val_a'].value()
                    old_val_b = old_ax['val_b'].value()
                    new_min = ax['valminmax'][0]*uf
                    new_max = ax['valminmax'][1]*uf
                    
                    #Force the old value range into the new min/max
                    val_a = self.forceInRange(old_val_a, new_min, new_max)
                    val_b = self.forceInRange(old_val_b, new_min, new_max)
                    
                    #Set the range for the new value cells
                    ax['val_a'].setRange(new_min, new_max)
                    ax['val_b'].setRange(new_min, new_max)
                    
                    #Calculate and set indices close to these values, then
                    #update the values to be an exact match
                    ind_a = self.valToInd(old_val_a, ax['ax'], ax['unit_factor'])
                    ind_b = self.valToInd(old_val_b, ax['ax'], ax['unit_factor'])
                    val_a = self.indToVal(ind_a, ax['ax'], ax['unit_factor'])
                    val_b = self.indToVal(ind_b, ax['ax'], ax['unit_factor'])
                    ax['ind_a'].setValue(ind_a)
                    ax['ind_b'].setValue(ind_b)
                    ax['val_a'].setValue(val_a)
                    ax['val_b'].setValue(val_b)
                    

        #If new axes match old ones, set the cur_axes to match
        if len(self.last_axes) != 0:
             cur_name = self.last_axes[ self.last_cur_axes[0] ]['name']
             ind = self.dropdown1.findText(cur_name)
             if ind != -1:
                 self.dropdown1.setCurrentIndex(ind)
             if self.plottype_field.currentIndex() == 1:
                 cur_name = self.last_axes[ self.last_cur_axes[1] ]['name']
                 ind = self.dropdown2.findText(cur_name)
                 if ind != -1:
                     self.dropdown2.setCurrentIndex(ind)
                
        #Once all the fields have been created, make sure they are set correctly
        self.updateAxesFields()
        self.showAvgAction()
        self.showFilterAction()
        


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
           #is_avg = ax['avgcheckbox'].isChecked()
           #ax['ind_a'].setDisabled(is_avg)
           #ax['val_a'].setDisabled(is_avg)

           #b is only enabled when it is the current axis AND not averaged
           if i in self.cur_axes or ax['avgcheckbox'].isChecked()==True :
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
                val_a = ax['val_a'].value()
                val_b = ax['val_b'].value()
                ind_a = self.valToInd(val_a, ax['ax'], ax['unit_factor'])
                ind_b = self.valToInd(val_b, ax['ax'], ax['unit_factor'])
                ax['ind_a'].setValue(ind_a)
                ax['ind_b'].setValue(ind_b)
                
           elif ax['indbtn'].isChecked():
                ind_a = int(ax['ind_a'].value())
                ind_b = int(ax['ind_b'].value())
                val_a = self.indToVal(ind_a, ax['ax'], ax['unit_factor'])
                val_b = self.indToVal(ind_b, ax['ax'], ax['unit_factor'])
                ax['val_a'].setValue(val_a)
                ax['val_b'].setValue(val_b)
                
               
           #Update the label for each line
           if ax['valbtn'].isChecked():
               #Currently using values, format label to match
               lbltxt = ('Values [' + self.numFormat(ax['valminmax'][0]*ax['unit_factor']) +
                         ', ' + self.numFormat(ax['valminmax'][1]*ax['unit_factor']) +
                         '] ' + ax['unit_field'].text())
           else:
                #Currently using indices, format label to match
                lbltxt = ('Indices [' + self.numFormat(ax['indminmax'][0]) +
                          ', ' + self.numFormat(ax['indminmax'][1]) +
                          ']')
           
           ax['rangelabel'].setText(lbltxt)
    
          
    
     
     #ACTION FUNTIONS (tied to buttons/fields/etc.)
    def showAvgAction(self):
        for ax in self.axes:
            if self.showAvg.isChecked():
                for x in ax['avgbox_widgets']:
                    x.show()
            else:
                for x in ax['avgbox_widgets']:
                    x.hide()
                    
    def showFilterAction(self):
        for ax in self.axes:
            if self.showFilter.isChecked():
                for x in self.filterbox_widgets:
                    x.show()
            else:
                for x in self.filterbox_widgets:
                    x.hide()
                    
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
         
         
    def updateDataUnits(self):
         if self.debug:
             print("Updating data units")
         try:
              #Update the data units first
              u = units.Unit(self.data_unit_field.text(), parse_strict='raise', format='ogip')
              cu = units.Unit(self.data_cur_unit , parse_strict='raise', format='ogip')
              nu = units.Unit(self.data_native_unit, parse_strict='raise', format='ogip')
              self.data_unit_factor =  ( (1 * nu).to(u) ).value 
              cur_unit_factor = ( (1 * nu).to(cu) ).value
              
              datarange_a_val = float(self.datarange_a.text())
              datarange_b_val = float(self.datarange_b.text())

              self.datarange_a.setValue(datarange_a_val*self.data_unit_factor/cur_unit_factor)
              self.datarange_b.setValue(datarange_b_val*self.data_unit_factor/cur_unit_factor)
              
              self.data_cur_unit = self.data_unit_field.text()
              
              self.makePlot()
         except ValueError:
              self.warninglabel.setText("WARNING: Unit string is invalid: " + str(self.data_unit_field.text()) )
  
    def updateAxesUnits(self, thisax):
         if self.debug:
             print("**********Updating axis units**********")
         try:
              #Repeat the calculation for each axis
              for i, ax in enumerate(self.axes):
                   #Only recauclate the units for the axis associtated with the fcn call
                   if ax == thisax:
                       if self.debug:
                            print("Unit label text: " + str(ax['unit_field'].text()))
                            print("Current Unit Displayed: " + str(ax['disp_unit']))
                            print("Axis Native Unit: " + str(ax['native_unit']))
                            print("Axis Unit Factor: " + str(ax['unit_factor']))
                        
                       u = units.Unit(ax['unit_field'].text(), parse_strict='raise', format='ogip')
                       cu = units.Unit(ax['disp_unit'], parse_strict='raise', format='ogip')
                       nu = units.Unit(ax['native_unit'], parse_strict='raise', format='ogip')
         
                       #New unit factor in relation to the native units
                       new_uf =  (1 * nu).to(u).value
                       #Old (currently displayed) unit factor in relation to native units
                       old_uf =  (1 * nu).to(cu).value
                       
                       #Temporarily store the values so they don't get messed up
                       #by the changing of the range
                       val_a = ax['val_a'].value()
                       val_b = ax['val_b'].value()
                       
                       mod_uf = new_uf/old_uf

                       #These are modified just by the new_uf,
                       #because they are stored always in native units
                       valmin = ax['valminmax'][0]*new_uf
                       valmax = ax['valminmax'][1]*new_uf

    
                       #Convert the range of the value fields
                       ax['val_a'].setRange(valmin, valmax)
                       ax['val_b'].setRange(valmin, valmax)
                       
    
                       #Convert the value axis fields to the new units
                       ax['val_a'].setValue( val_a*mod_uf)
                       ax['val_b'].setValue( val_b*mod_uf)
                       
                       #Update the "current" unit variables
                       ax['disp_unit'] = ax['unit_field'].text()
                       ax['unit_factor'] = new_uf
                       
                       if self.debug:
                            print("*Calculation*")
                            print("Current Unit Displayed: " + str(ax['disp_unit']))
                            print("Axis Native Unit: " + str(ax['native_unit']))
                            print("Axis Unit Factor: " + str(ax['unit_factor']))

              self.updateAxesFields()
              self.makePlot()
         except ValueError:
              self.warninglabel.setText("WARNING: Unit string is invalid: " + str(ax['unit_field'].text()) )
              
    def updateDataRange(self):
         if self.debug:
             print("Updating data range")
         if self.datarange_center.isChecked():
              self.datarange_a.setDisabled(True)
              self.datarange_a.setValue(- self.datarange_b.value() )
         else:
              self.datarange_a.setDisabled(False)
         self.makePlot()
              
        



    #PLOTTING ROUTINES
    
    def validateChoices(self):
       if self.debug:
             print("Validating choices")
       #Make a temporary array of the axes that are ACTUALLY about to be
       #plotted (ignoring 2nd one if the plot is 2D)
       if self.plottype_field.currentIndex() == 0:
            thisplot_axes = [self.cur_axes[0]]
       elif self.plottype_field.currentIndex() == 1:
            thisplot_axes = self.cur_axes
      
         
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
      
       #Check to make sure the axes make sense
       for ind, ax in enumerate(self.axes):
           if ind in thisplot_axes:
               a = int(ax['ind_a'].value())
               b = int(ax['ind_b'].value())
               #Range should not be zero!
               if np.abs(b - a) < 2:
                   self.warninglabel.setText("WARNING: Axes range is must be greater than 2!")
                   return False
               #Order of elements in range should be correct!
               elif a  > b:
                   self.warninglabel.setText("WARNING: First range element should be smallest!")
                   return False
   
                   

       #If no warnings are found, set the label to blank and return True
       self.warninglabel.setText("")
       return True

    def makePlot(self):
        if self.debug:
             print("Making plot")
        self.clearCanvas()
        try:
            if self.validateChoices():
                self.getData()
                
                self.applyDataFunctions()
                
                if self.plottype_field.currentIndex() == 0:
                    self.plot1D()
                elif self.plottype_field.currentIndex() == 1:
                    self.plot2D()
        except ValueError as e:
            print("Value Error!: " + str(e))
            print(traceback.format_exc())
        except IndexError as e:
            print("Index Error!: " + str(e))
            print(traceback.format_exc())
   
    
    def applyDataFunctions(self):
        if self.lowpass_checkbox.isChecked():
            sigma = self.filter_sigma.value()
            self.data = ndimage.gaussian_filter(self.data, sigma)
        elif self.highpass_checkbox.isChecked():
            sigma = self.filter_sigma.value()
            self.data = self.data - ndimage.gaussian_filter(self.data, sigma)

    
    def clearCanvas(self):
        if self.debug:
             print("Clearing canvas")
        try:
            self.figure.clf()
            self.canvas_ax.clear()
            self.canvas.draw()
        except AttributeError as e:
            pass
        
    def clearLayout(self, layout):
        if self.debug:
             print("Clearing layout")
        if layout !=None:
            while layout.count():
                child = layout.takeAt(0)
                if child.widget() is not None:
                    child.widget().deleteLater()
                elif child.layout() is not None:
                    self.clearLayout(child.layout())
                    
                    
    def hideLayout(self, layout):
        if self.debug:
             print("Hiding layout")
        if layout !=None:
            for i in range(layout.count()):
                w = layout.takeAt(i).widget()
                w.hide()
                
    def showLayout(self, layout):
        if self.debug:
             print("Showing layout")
        if layout !=None:
            for i in range(layout.count()):
                w = layout.takeAt(i).widget()
                w.show()
                    
                    
    def getData(self):
        if self.debug:
             print("Getting Data From File")
        dslice = []
        
        avg_axes = []
        
        
        loaded_axes = 0
        if self.plottype_field.currentIndex() == 0:
            hax_ind = self.cur_axes[0]
            vax_ind = -1
        elif self.plottype_field.currentIndex() == 1:
            hax_ind = self.cur_axes[0]
            vax_ind = self.cur_axes[1]

        for i, ax in enumerate(self.axes):
                if i == hax_ind or i == vax_ind:
                    a = int(ax['ind_a'].value())
                    b = int(ax['ind_b'].value())
                    dslice.append( slice(a, b, 1) )
                    loaded_axes += 1
                    if i == hax_ind:
                         self.hax['name'] = ax['name']
                         self.hax['slice'] = slice(a,b, 1)
                         self.hax['unit'] = ax['unit_field'].text()
                         self.hax['unit_factor'] = ax['unit_factor']
                    elif i == vax_ind:
                         self.vax['name'] = ax['name']
                         self.vax['slice'] = slice(a,b, 1)
                         self.vax['unit'] = ax['unit_field'].text()
                         self.vax['unit_factor'] = ax['unit_factor']
                elif ax['avgcheckbox'].isChecked():
                    a = int(ax['ind_a'].value())
                    b = int(ax['ind_b'].value())
                    dslice.append( slice(a, b+1, 1) )
                    avg_axes.append(loaded_axes)
                    loaded_axes += 1
                    
                else:
                    a = int(ax['ind_a'].value())
                    dslice.append( slice(a, a+1, 1) )
            
        with h5py.File(self.filepath, 'r') as f:
                self.hax['ax'] = np.squeeze(f[self.hax['name'] ][self.hax['slice']])*self.hax['unit_factor']
                self.data  = np.squeeze(f['data'][tuple(dslice)])*self.data_unit_factor
                
                
                
                #If selected, apply averaging
                if len(avg_axes) != 0:
                    print(self.data.shape)
                    print(avg_axes)
                    self.data = np.mean(self.data, axis=tuple(avg_axes))
                
                
                #If 2D plot, do the vertical axis too
                if self.plottype_field.currentIndex() == 1:
                    self.vax['ax'] = np.squeeze(f[self.vax['name'] ][self.vax['slice']])*self.vax['unit_factor']
                    if vax_ind > hax_ind:
                        self.data = self.data.transpose()
                

    def plot1D(self):
        if self.debug:
             print("Making 1D plot")

        self.canvas_ax = self.canvas.figure.subplots()

        self.canvas_ax.plot(self.hax['ax'], self.data, linestyle='-')
        
        self.canvas_ax.set_xlabel(str(self.hax['name']) + ' (' + str(self.hax['unit']) + ')')
        self.canvas_ax.set_ylabel('(' + str(self.data_unit_field.text()) + ')')
        
        if self.plot_title_checkbox.isChecked():
            title = self.plotTitle()
            self.canvas_ax.set_title(title)

        #Setup axis formats
        self.canvas_ax.ticklabel_format(axis='x', scilimits=(-3,3) )
        self.canvas_ax.ticklabel_format(axis='y', scilimits=(-3,3) )
        
        #Autorange if appropriate
        if self.datarange_auto.isChecked():
             if self.datarange_center.isChecked():
                  datamax = np.max(self.data)
                  datamin = - datamax
             else:
                  datamax = np.max(self.data)
                  datamin = np.min(self.data)    
        else:
            datamin = float(self.datarange_a.text())
            datamax = float(self.datarange_b.text())
        self.canvas_ax.set_ylim(datamin, datamax)
        self.canvas.draw()

    
    
    def plot2D(self):
        if self.debug:
             print("Making 2D plot")

        if self.datarange_auto.isChecked():
            if self.datarange_center.isChecked():
                 cmax = np.max(self.data)
                 cmin = - cmax
            else:
                cmin = np.min(self.data)
                cmax = np.max(self.data)
        else:
            cmin = float(self.datarange_a.text())
            cmax = float(self.datarange_b.text())
            
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
            cs = self.canvas_ax.contourf(self.hax['ax'], self.vax['ax'], self.data, levels, cmap=colormap)
        else:
            cs = self.canvas_ax.imshow(self.data, origin='lower',
                                       vmin=cmin, vmax=cmax,
                                       aspect='auto', interpolation = 'nearest',
                                       extent=[self.hax['ax'][0], self.hax['ax'][-1], 
                                               self.vax['ax'][0], self.vax['ax'][-1]],
                                       cmap = colormap)

        if np.max( np.abs(self.data ) ) > 100 or np.max( np.abs(self.data ) ) < 0.01:
            cbformat = '%.1e'
        else:
            cbformat = '%.1f'

        cbar = self.canvas.figure.colorbar(cs, orientation='horizontal', 
                                           format=cbformat)
        cbar.ax.set_xlabel('(' + str(self.data_unit_field.text()) + ')' )
        
        self.canvas_ax.set_xlabel(str(self.hax['name']) + ' (' + str(self.hax['unit']) + ')')
        self.canvas_ax.set_ylabel(str(self.vax['name']) + ' (' + str(self.vax['unit']) + ')')

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
                 val = ( self.numFormat(axarr[a]*ax['unit_factor']),
                         self.numFormat(axarr[b]*ax['unit_factor']),
                         ax['unit_field'].text())
                 curarr.append( ax['name'] + '=[%s,%s] %s' % val )
             elif ax['avgcheckbox'].isChecked():
                 otherarr.append( ax['name'] + '= avg' )
             else:
                 val = ( self.numFormat(axarr[a]*ax['unit_factor']),
                         ax['unit_field'].text())
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
       
          
    def valToInd(self, val, ax, unit_factor):
         ind = np.argmin(np.abs(ax*unit_factor - val))
         return ind
    
    def indToVal(self, ind, ax, unit_factor):
         val = ax[ind]*unit_factor
         return val
    
     
    def forceInRange(self, x, a, b):
         if x > b:
              return b
         elif x < a:
              return a
         else:
              return x
         
     
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
        self.setMinimum(-np.inf)
        self.setMaximum(np.inf)
        self.validator = FloatValidator()
        self.setDecimals(1000)

    def validate(self, text, position):
        return self.validator.validate(text, position)

    def fixup(self, text):
        return self.validator.fixup(text)

    def valueFromText(self, text):
        return float(text)

    def textFromValue(self, value):
        #print('FORMATTING: ' + str(value) + ' -> ' + str(format_float(value)))
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
        #print('QApplication instance already exists: %s' % str(app))
        pass

    w = ApplicationWindow()
    w.show()
    app.exec()