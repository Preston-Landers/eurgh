## Eurgh! ##

Eurgh is a developer tool to translate message catalogs (.po files) using 
Microsoft Translator API. It can also perform translations of plain text files or stdin.
You tell Eurgh where your message catalogs are and Eurgh calls out to the Microsoft
Translator API to translate the strings in your catalog.

This is not intended to provide a production quality translation; only to fill in a very
rough translation that can be further tweaked by humans. 

If you plan to run this tool on your source code files you should be using version control such 
as git just in case it mangles your files.

This tool deals with standard gettext message catalogs and can be used with any
programming language that handles gettext-style message catalogs (po/mo files).
Understanding how to work with these files and internationalize your app is beyond
the scope of this documentation.

Python users may want to start here:

http://docs.pylonsproject.org/projects/pyramid/en/latest/narr/i18n.html

http://babel.pocoo.org/

https://docs.python.org/2/library/gettext.html

https://pypi.python.org/pypi/lingua

## Supported Languages ##

Supported language codes are here:

http://msdn.microsoft.com/en-us/library/hh456380.aspx

## Requirements ##

You need Python 2 or 3 to run this program. The package 'babel' will be installed by 
this tool's setup.py script if not already available.

You should have some source code with a locale directory where you have subdirectories 
for each language. For instance, imagine your app source code is:

    /myapp
    /myapp/src/locale
    /myapp/src/locale/myapp.pot
    /myapp/src/locale/ja/LC_MESSAGES/myapp.po
    /myapp/src/locale/de/LC_MESSAGES/myapp.po

In order to use Eurgh you must first register on the Microsoft Azure Data Market:

https://datamarket.azure.com/developer/applications

Register a new "application" and obtain an OAuth client ID and secret. The application
you register here doesn't necessarily have to be related to your real app. It's just
a way to track API requests.

Then you must subscribe to at least the free tier of the Microsoft Translator data set.

## Install ##

Download the source code into a directory.

    $ python setup.py install

## Command Line Usage ##

Eurgh can be used to do translations on the command line.

TODO: this part is not finished yet.


## Translating Application Message Catalogs ##

Edit eurgh.ini (or copy it to local.ini first, or a different file).

Put in your client ID, secret, and the path to your application source's locale
directory.

Also indicate the languages you want translated. Only languages listed in your .ini
file will be translated. You may also need to specify the message domain and encoding.

Each language you list must already have an existing .po file in the correct 
location. For example, if using Babel with Python you can generate a .po file like:

    $ pybabel init -l ja -i /path/to/app/src/locale/myapp.pot -d /path/to/app/src/locale -D myapp

Now run Eurgh it like:

    $ eurgh local.ini

NOTE: for now you must actually run it like:

    $ python -m eurgh local.ini

Your message catalogs should now be updated.  Please review and edit the translations. 
Now you can compile the message catalog and recompile your app. For example, Python users 
might do this in their own app source code directory:
    
    $ python setup.py compile_catalog


## FAQ ##

### Where does the name come from? ###

The Babel Fish is small, yellow, and simultaneously translates from one spoken language to another.

When inserted into the ear, its nutrition processes convert sound waves into brain waves, neatly crossing the 
language divide between any species you should happen to meet whilst travelling in space.

Some say that the evolution of the Babel fish could not have been accidental, and hence that it proves the 
non-existence of God.

Arthur Dent, a surviving Earthling, commented only 'Eurgh!' when first inserting the fish into his ear canal. It did, 
however, enable him to understand Vogon Poetry - not, necessarily, a good thing.
