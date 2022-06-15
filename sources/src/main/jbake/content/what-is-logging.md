title=What is logging?
status=published
type=page
~~~~~~

[TOC bullet hierarchy levels=1-3]

# What is logging?
At a high level, logging is used to capture information during the run of an
application.  This can include different types of information about both the
state of the application and inputs to the application.  For example, an HTTP 
server may log information about incoming connections(such as an IP address).  
Logging can also be at different levels of verbosity, in order to allow a user 
of the application to not be overwhelmed with too much information.

Logging can be broadly classified into two categories.  The two main categories 
of logging are debug logging and audit logging.  Debug logging is generally 
useful for application developers who can turn on messages that an end-user 
does not care about - for example, if data is being parsed correctly, or if an 
exception is thrown.  Audit logging is more interesting to system 
administrators.  This type of data would include information such as when 
somebody logged in, who changed a piece of information, etc.  Debug logging and 
audit logging are not mutually exclusive, and there can be plenty of overlap 
between these two categories.

# What should a logging framework do?
At a minimum, a logging framework needs to be able to do the following:

* Easily allow you to create log messages
* Send log messages to stdout and/or stderr
* Be completely transparent to your application - your application should 
behave exactly the same no matter if logging is enabled or disabled

However, a logging framework that does only these things is not particularly 
useful, and no better than using `System.out.println()` or `printf()`.  Common 
features of logging frameworks generally include:

* Ability to send log messages to other places than just stdout/stderr.  For 
example, common places to send logs could be:
   1. syslog
   2. A file on the local filesystem
   3. Remote log server(e.g. ELK, Splunk, kibana, etc.)
   4. Windows event log
   5. Database
* Filtering based off of levels and data
* Location information of where the log statement is in the code
* Allow for rotation of files when logging to a file.  This allows you to do 
things such as creating a new log whenever you start up, doing one log file per 
day, limiting files to a specific size, etc.
* Log to multiple locations at once(send the same data to stdout and a file for 
example)
* Classify messages based off of the particular subsystem that they are from
* Format log messages according to some user-defined pattern

This is not an exhaustive list of all features that could exist.  There are 
many different logging frameworks that exist which may implement different 
subsets of these features, and may also have more features than are listed here.

# Log Levels and Subsystem Classification
When you are logging information, two of the most important things to know are 
the level of the log message and the subsystem that the log message is from.  
This allows you to determine how severe something is, as well as where it is 
coming from.

The traditional log levels are as follows(from most verbose to least verbose):
TRACE
DEBUG
INFO
WARN
ERROR

In addition, levels of CRITICAL and FATAL may exist as well.  Generally, FATAL 
indicates that the application is about to exit, while CRITICAL is similar to 
ERROR.

Levels make it easy to quickly filter messages.  Since more verbose messages 
still allow less verbose messages to be printed, you don't lose information by 
turning the verbosity up.  When you are working on a particular subsystem, you 
may want that subsystem to be at the DEBUG level to see all the messages, or 
TRACE if there is something that you really need to see.  As a general rule of 
thumb, when your application is in production the default level of all loggers 
should be at the INFO level.

Subsystems help to classify the data as well.  In Java, this is generally done 
by the package that a class is in.  Being able to set a particular subsystem 
that you are debugging to the DEBUG level(and not just a single class) is an 
important part of being able to easily filter information and to not overload 
the programmer who is debugging the application.

Within the Apache Logging Services projects(log4j2, log4cxx, and log4net) this 
subsystem classification follows the Java hierarchical approach.  If you have a 
logger org.apache.Foo and org.apache.Bar, you can set the level of org.apache 
to DEBUG and both loggers will be at the DEBUG level, but can also be 
individually set if required.  This hierarchical way of logging is not a 
feature that all logging frameworks have, however it is very useful if your 
code is organized in a way such that all classes have individual loggers and 
are logically separated into subsystems appropriately.  This also allows for 
more granular control over your debug statements.

# Where to put logs?
Logging to different locations(sometimes called sinks) is an important part of 
logging frameworks.  For simple applications, you may not need to do anything 
more complicated than just send data to stdout and/or a file.  However, more 
complicated applications quickly need to have more flexibility in how and where 
they log information.  Modern applications can log to web-based log aggregators 
in addition to a local log mechanism such as syslog.

By configuring these log locations through an external source such as a config 
file, it also makes it possible for the end-user to configure the system for 
their particular use-case.

# Transparent Logging
One of the most basic tenets of logging is that it needs to be completely 
transparent to your application.  Your application must not care if logging is 
enabled or disabled: all it does is send messages to the logging framework, 
which then handles all of the filtering and routing required to get the message 
to its final destination.  This also makes it possible to write unit tests that 
don't care about logging at all.  If the logging system is not initialized, the 
worst that should happen is that nothing gets logged.

# How to do proper logging
Now that we understand what the normal features of logging libraries are, 
it’s time to talk about how to do proper logging.  As we’ve mentioned 
before, the two main things to worry about when logging are what the level of 
the message is, and the classification of the log message.  For the 
classification of the log message, this will often be the name of the class 
that is doing the logging.  Assuming that you have a good design already, then 
the classification derives clearly from the name of the class and the 
package/namespace the class is in.

Choosing the level of the log message can be a bit trickier.  A good rule of 
thumb is to leave your log messages at INFO level during normal operation, so 
what should we put at that level and what should be more verbose?  Let’s 
assume that we are opening a network socket for remote communications.  At the 
INFO level we may inform that the network subsystem is starting up and ready 
for work.  DEBUG information could include new connections from clients with 
their IP/port combination, while TRACE information could be output whenever a 
packet comes in from a client.  In addition, we may have ERROR messages if we 
are unable to open a socket for reading/writing.

By having different pieces of the data flow at different log levels, it makes 
it easy to quickly look at the logs and determine how serious a problem is and 
what the system is doing during operation.

# Other things to worry about when logging
As we have seen, having a good logging framework is critical to being able to 
find and fix errors in applications.  However, just because we have logging 
doesn’t mean that it is infallible.  Since logging code that you insert into 
your application is still code that you have written, it is always possible 
that the log messages you get out are lying to you due to a bug in a log 
statement.  

# Features that the Apache Logging Services projects have
While there are many different logging frameworks that exist for Java, C++, and
.NET, there are a number of built-in features that Log4j2, Log4cxx, and Log4net
have that are generally useful.

## Hierarchichal Logging
As mentioned previously, hierarchical logging allows for easy grouping of
subsystem information.  This allows you to have fine-grained control over the
information that you are logging and easily allows for one logger per-class.

This hierarchical logging also means that you don't need to explicitly share
a sink between loggers.  While it is possible to configure Log4j2 and Log4cxx
to send each logger to a separate location, the parent/child relationship means
that children will log their messages to any sinks that their parents have.

## Location Information
Knowing exactly where a log statement is can be vital in order to track down
the location of a log statement.  Both Log4j2 and Log4cxx are able to determine
the filename, class name, method name, and line number where the log message
is coming from.  With Log4cxx, this is able to be done at compile-time.

## Static and Single-instance Loggers
All loggers that are created with Log4j2 and Log4cxx are able to be declared
as static variables in your source file, eliminating the need for a dedicated
instance variable of a logger per-class.  A side effect of this is that there
is a global logger registry, so that you can access the same logger via a
static LogManager in different classes without having to pass the logger around.

## Nested and Mapped Diagnostic Contexts
When you have multiple objects of the same type, using a static logger can be
problematic when you need to only view data for one instance of the class.  By
providing a Nested Diagnostic Context and a Mapped Diagnostic Context, it is
possible to add context information to your log statements.

## Flexible Log Message Formatting
When sending a log message to a flat text file, it is often desirable to have
the messages in a simple to understand format.  This information can include
data such as the date/time of the log message, the level of the message, the
logger that produced the message, and the message itself.  With the Log4j2
and Log4cxx PatternLayout classes, it is possible to quickly configure the
logging system to output information in a convenient format.

Different types of log message formatting is also important when you need
to send messages to different locations.  The code that creates the log messages
should not know anything about how the message is formatted on the backend.
This allows for the same log message to be formatted in different ways with
potentially different metadata - for example, JSON format for a log aggregating
service, or plain text for a local configuration file.

## Configuration via config file
Both Log4j2 and Log4cxx can be configured with a configuration file in one of
several different formats.  While it is always possible to configure via code,
configuration files make it easy to reconfigure the system without having to
recompile your code.  This also means it is possible to edit a configuration
file and dynamically change the configuration at runtime.  For example, you
can turn on a logger that was previously off if you are debugging a live
system.

## Garbage-free(Log4j2)
In Java, it is important to reduce the amount of time that the garbage
collector takes to run.  By not allocating and freeing objects, your
log statements will add very little to the runtime overhead of your application.

## Formatting with replacements
When creating a log statement, it is often slow and annoying to perform string
concatenation to create a log statement.  In Java, the simplest way to
concatenate a string is to simply use the + operator:

```
log("Logging information: " + someVariable + " and the other variable is " + otherVariable);
```

While in C++, you can get into a chevron overload:

```
log("Logging information: " << someVariable << " and the other variable is " << otherVariable);
```

Both Log4j2 and Log4cxx allow for variable replacements in strings, such that
the above log statements can both be written similar to the following:

```
log("Logging information: {} and the other variable is {}", someVariable, otherVariable);
```

## Filtering
When you have many different log messages that you are trying to make sense of,
it can be difficult to focus on the correct piece of information.  Because of
this, it is possible to configure both Log4j2 and Log4cxx to filter certain
messages based off of various attributes, such as a text string that is contained
within the log message.  Since these filters are also able to be configured
through the confgiuration file, adding or removing filters is a simple operation.

# Conclusion
Logging is a rather complicated topic that covers many different aspects.  While
different applications will have different requirements for their log statements,
the projects of the Apache Logging Services Commitee provide a generic and
widely applicable implemenation of logging for all kinds of applications.

