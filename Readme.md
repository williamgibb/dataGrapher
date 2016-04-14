dataGrapher
=====

This is a simple project for storing and plotting realtime data obtained from Mettler-Toledo NewBalance scales.
This plots the measured weight and the change in weight over time (specifically the 1st order discrete difference).

Data is stored in a sqlite database, and is visualized in realtime using Vispy.

To Use
=====

This is a python 3 project.  It has been developed on python 3.4, but should also work on python 3.5.  It will not
work on python 2.7.  It does not have a GUI to control it, all functionality is passed via the command line.

1. Clone this repository using git
1. Install requirements using "pip install -r requirements".
1. Run the application using "python -m app".

When running in collection or replay mode, simply clossing the plot window or issuing a keybaord interrupt (Control + C)
will gracefully shut down the application.

Command line args
=====

Running the app w/o arguments will show the default help.  Sub commands are used to specify different actions.

```
    $ python -m app -h
    usage: __main__.py [-h] [-d DB] [-v] {collect,list,ports,dump,replay} ...
    
    Runs the datagrapher application.
    
    positional arguments:
      {collect,list,ports,dump,replay}
                            sub-command help
        collect             Collect, graph and store data.
        list                List session collection data
        ports               List serial ports available for use
        dump                Dump session collection data
        replay              Replay the visualization for a given session
    
    optional arguments:
      -h, --help            show this help message and exit
      -d DB, --db DB        Name of the db to store data into
      -v                    Enable verbose output
```

By default, a database 'test.db' is created if no db is specified.

The collect command is used to actually collect data from a balance, or to run tests.

```
    $ python -m app collect -h
    usage: __main__.py collect [-h] [-t {None,random,sawtooth}] [-c NAME]
                               [-n NOTES] [-u USER] [-p PORT] [-s]
    
    optional arguments:
      -h, --help            show this help message and exit
      -t {None,random,sawtooth}, --test {None,random,sawtooth}
                            Perform a data capture and serialization test.
      -c NAME, --collection-name NAME
                            Name of the data collection
      -n NOTES, --notes NOTES
                            Notes related to the data collection
      -u USER, --username USER
                            User performing the data collection
      -p PORT, --port PORT  Serial port to connect to in order to collect data.
      -s, --stable-only     Only record stable values
```

The tests generate random values or a sawtooth wave of data.  These can be used as a end-to-end test of the program.
The name option allows you to specify the name of a given data collection.
The notes option allows you to specify notes for a given data collection.
The user option allows you to specify the researcher performing the data collection.
The port option allows you to specify which serial port to connect to.  This should be a serial port that can be used 
by pyserial.  
The stable option allows you to specify if you only want data values recorded that are stable reading from the balance.


To find out what serial ports you currently have available, you can issue the following command.  It will call the
pyserial list_ports command to find out what serial ports are available to your system.

```
$python -m app ports
/dev/cu.Bluetooth-Incoming-Port
1 ports found
```

The list command will list data about all of the sessions stored in the database.  For exxample:

```
$ python -m app list
+----+----------------+----------+----------------------------+----------------------------+-------+
| id | name           | notes    | start                      | stop                       | user  |
+----+----------------+----------+----------------------------+----------------------------+-------+
| 1  | Collection     | None     | 2016-04-03 15:08:46.328586 | 2016-04-03 15:10:30.736098 | wgibb |
| 2  | Collection     | None     | 2016-04-04 00:31:06.181298 | 2016-04-04 00:31:36.710248 | wgibb |
...
```

The dump command will dump the data collected in a given session to a xlsx file.  This is done by specifying the id 
obtained from the list command.

```
$ python -m app dump -i 1 -o test.xlsx 
04/13/2016 09:04:35 PM:INFO: Writing data to [test.xlsx] [__main__.dump_session_data]
```

It is also possible to re-visualize data that has been collected and stored in the database with the replay command. 
For example, to replay back the data from the first session in 0.1 second increments, you can use the following command:
```
$ python -m app replay -r 0.1 -i 1
```


TODO
====
1. Support customer arguments for the serial connections.
1. Migrate to using vispy's plot interface instead of using a hacked up set of example code.
1. Add a proper UI.

