
##################
# imports
from Tkinter import *
from ScrolledText import *
from eventBasedAnimationClass import EventBasedAnimationClass
from StringIO import StringIO
from thread import *
import operator # for sorting dict
import threading
import socket
import sys
import os, re , collections, string
import tkFont
import tkFileDialog
import tkMessageBox
import tkSimpleDialog
import string
import pygments
import pygments.lexers
import pygments.styles
import compiler, parser, traceback
import time
##################

class TextEditor(EventBasedAnimationClass):

    @staticmethod
    def make2dList(rows, cols):
        # From 15-112 class notes
        a=[]
        for row in xrange(rows): a += [[0]*cols]
        return a

    @staticmethod
    def readFile(filename, mode="rt"):
        # From 15-112 class notes
        # rt = "read text"
        with open(filename, mode) as fin:
            return fin.read()

    @staticmethod
    def writeFile(filename, contents, mode="wt"):
        # From 15-112 class notes
        # wt = "write text"
        with open(filename, mode) as fout:
            fout.write(contents)


    def highlightError(self, lineNumber):
        # highlights error in the code based on line number
        self.textWidget.tag_remove("error",1.0,END)
        self.textWidget.tag_add("error", "%d.0"%lineNumber,
            "%d.end"%lineNumber)
        self.textWidget.tag_config("error", underline = 1)

    def colorIsBlack(self, color):
        # ranks whether a color is nearing black or white
        color = color[1:]
        count = int(color,16)
        if(count<(16**len(color) -1 )/2):
            return True
        return False

    def styleTokens(self,tokenisedText,colorScheme,
                    startIndex,seenlen,seenLines,flag):
        # apply style to tokens in the text
        for token in tokenisedText:
            styleForThisToken = colorScheme.style_for_token(token[0])
            if(styleForThisToken['color']):
                self.currentColor = "#" + styleForThisToken['color'] 
            else:
                if(self.colorIsBlack(colorScheme.background_color)):
                    self.currentColor = "White"
                else: self.currentColor = "Black"
            if(token[1] == "\n"): seenLines += 1
            if(seenLines > 23 and flag): break
            # the '#' is to denote hex value
            textWidget = self.textWidget
            newSeenLen = seenlen + len(token[1])
            textWidget.tag_add(startIndex+"+%dc"%seenlen,
                startIndex+"+%dc"%(seenlen),
                startIndex+"+%dc"%(newSeenLen))
            self.textWidget.tag_config(startIndex+"+%dc"%seenlen,
                foreground = self.currentColor)
            seenlen = newSeenLen

    def checkErrors(self):
        # checks whether there is an error in the code by parsing it
        # and analysing the traceback
        errors = MyParse().pythonCodeContainsErrorOnParse(self.currentText)
        if(errors[0]):
            try:
                lineNumber=int(errors[1][-5][errors[1][-5].find("line ")+5:])
            except:
                lineNumber=int(errors[1][-7][errors[1][-7].find("line ")+5:])
            self.highlightError(lineNumber)
        else:
            self.textWidget.tag_remove("error",1.0,END)

    def highlightText(self,lineCounter = "1",columnCounter = "0",flag = False):
        # highlight text since syntax mode is on
        text = self.currentText.split("\n")
        text = "\n".join(text[int(lineCounter)-1:])
        startIndex = lineCounter + "." + columnCounter
        seenlen, seenLines = 0,0
        tokenisedText = pygments.lex(text, self.lexer)
        if(self.colorScheme):
            colorScheme = pygments.styles.get_style_by_name(self.colorScheme)
        else:
            colorScheme = pygments.styles.get_style_by_name(
                self.defaultColorScheme)
        if(self.colorIsBlack(colorScheme.background_color)):
            self.insertColor = "White"
        else: self.insertColor = "Black"
        self.textWidget.config(background = colorScheme.background_color,
            highlightbackground = colorScheme.highlight_color,
            highlightcolor = colorScheme.highlight_color,
            insertbackground = self.insertColor)
        self.styleTokens(tokenisedText,colorScheme,startIndex,seenlen,
            seenLines, flag)
        if(self.fileExtension == ".py" and self.errorDetectionMode):
            self.checkErrors()

    def editDistance(self,currentWord, word):
        # wagner-fischer algorithm for calculating levenshtein distance
        dp = TextEditor.make2dList(len(currentWord)+1, len(word)+1)
        costOfInsertion = 1
        costOfDeletion = 1
        costOfSubstitution = 1
        for i in xrange(len(currentWord)+1):
            dp[i][0] = i*costOfInsertion
        for i in xrange(len(word)+1):
            dp[0][i] = i*costOfDeletion
        for i in xrange(1,len(currentWord)+1):
            for j in xrange(1,len(word)+1):
                if(currentWord[i-1] == word[j-1]):
                    dp[i][j] = dp[i-1][j-1]
                else:
                    dp[i][j] = min(dp[i][j-1]+costOfInsertion,
                            dp[i-1][j]+costOfDeletion,dp[i-1][j-1] + 
                            costOfSubstitution)
        return dp[len(currentWord)][len(word)]

    def wordsAreSimilar(self, currentWord, word):
        if(word.startswith(currentWord)):
            return True, abs(len(currentWord)-len(word))/2
        similarity = self.editDistance(currentWord, word)
        return float(similarity)/len(currentWord)<=.5,similarity 

    def cleanWord(self, word):
        # cleans a word by removing all not (char or numbers)
        processedWord = ""
        for c in word:
            if(c in string.ascii_uppercase or
                c in string.ascii_lowercase or 
                c in "1234567890"):
                processedWord += c
        return processedWord

    def sortSuggestionDict(self):
        # sorts suggestion dictionary
        self.suggestionDict = sorted(self.suggestionDict.items(),
             key=operator.itemgetter(1))

    def findMatchesToWord(self, currentWord):
        # checks words in current text and adds them to suggestionDict
        # based on whether they are similar or not
        if(currentWord == ""): return []
        listOfWords = self.currentText.split()
        for word in listOfWords:
            word = self.cleanWord(word)
            if word!= currentWord[:-1]:
                similar = self.wordsAreSimilar(currentWord, word)
                if(similar[0] and word not in self.suggestionDict):
                    self.suggestionDict[word] = similar[1]
        self.sortSuggestionDict
        return self.suggestionDict

    def getCurrentWord(self):
        # gets current word user is typing
        word = self.textWidget.get(self.textWidget.index("insert wordstart"), 
            self.textWidget.index("insert wordend"))
        if(word == "\n" or word == " "):
            word = self.textWidget.get(
                self.textWidget.index("insert -1c wordstart"), 
                self.textWidget.index("insert wordend"))
        word = word.replace("\n","")
        return word

    def openFile(self):
        # opens a file, also detects whether it is 
        # a program or not
        self.initProgrammingModeAttributes()
        path = tkFileDialog.askopenfilename()
        if(path):
            self.currentFilePath = path
            self.currentFile = os.path.basename(path)
            self.currentText = TextEditor.readFile(path)
            self.textWidget.delete(1.0,END)
            self.textWidget.insert(1.0,self.currentText)
            self.fileExtension = os.path.splitext(path)[1]
            self.root.wm_title(self.currentFile)
            if(self.fileExtension != ".txt" and
                pygments.lexers.guess_lexer_for_filename(
                    "example%s"%self.fileExtension,[])):
                self.programmingMode = True
                self.lexer = pygments.lexers.guess_lexer_for_filename(
                    "example%s"%self.fileExtension,[])
                self.highlightText()

    def saveFile(self):
        if(self.currentFilePath):
            TextEditor.writeFile(self.currentFilePath, self.currentText)

    def saveAs(self):
        # saves a file, automatically adds extension
        path = tkFileDialog.asksaveasfilename()
        if(path):
            if(self.fileExtension): path += self.fileExtension
            else: path += ".txt"
            TextEditor.writeFile(path, self.currentText)
            self.currentFilePath = path
            self.currentFile = os.path.basename(path)
            self.root.wm_title(self.currentFile)
            if(self.fileExtension !=".txt" and
                pygments.lexers.guess_lexer_for_filename(
                    "example%s"%self.fileExtension,[])):
                self.programmingMode = True
                self.lexer = pygments.lexers.guess_lexer_for_filename(
                    "example%s"%self.fileExtension,[])
                self.highlightText()

    def newTab(self):
        TextEditor(1500,50).run()

    def undo(self):
        self.textWidget.edit_undo()

    def redo(self):
        self.textWidget.edit_redo()

    def cut(self):
        if self.textWidget.tag_ranges("sel"):
            self.clipboard = self.textWidget.get("sel.first","sel.last")
            self.textWidget.delete("sel.first","sel.last")
        else:
            self.clipboard = ""

    def copy(self):
        if self.textWidget.tag_ranges("sel"):
            self.clipboard = self.textWidget.get("sel.first","sel.last")

    def paste(self):
        if self.textWidget.tag_ranges("sel"):
            self.textWidget.insert("insert",self.clipboard)

    def resetFontAttribute(self):
        self.font = tkFont.Font(family = self.currentFont,
            size = self.fontSize)
        self.textWidget.config(font = self.font)

    def increaseFontSize(self):
        self.fontSize += 2
        self.resetFontAttribute()

    def decreaseFontSize(self):
        self.fontSize -= 2
        self.resetFontAttribute()

    def highlightString(self,searchString):
        lenSearchString = len(searchString) 
        self.textWidget.tag_delete("search")
        self.textWidget.tag_config("search", background = "#FFE792")
        start = 1.0
        while True:
            pos = self.textWidget.search(searchString, start, stopindex = END)
            if(not pos):
                break
            self.textWidget.tag_add("search", pos, pos+"+%dc"%(lenSearchString))
            start = pos + "+1c"

    # search highlight color #FFE792
    def searchInText(self):
        title = "Search"
        message = "Enter word to search for"
        searchString = tkSimpleDialog.askstring(title,message)
        if(searchString == None): return
        self.highlightString(searchString)

    def commentCode(self):
        # puts an annotation in the currently selected text
        title = "Comment"
        message = "Enter comment for selection"
        comment = tkSimpleDialog.askstring(title,message)
        if(comment == None): return
        if self.textWidget.tag_ranges("sel"):
            self.textWidget.tag_add("comment",
                self.textWidget.index(SEL_FIRST),
                self.textWidget.index(SEL_LAST))
            self.textWidget.tag_config("comment", underline = 1)
            self.comments += [self.textWidget.index(SEL_FIRST) + "|" +
                self.textWidget.index(SEL_LAST) + "|" + comment]
            if(self.collaborativeCodingMode):
                # can only send strings through socket 
                self.client.sendData(";".join(self.comments))

    def findAndReplaceInText(self):
        # finds and replaces a word
        title = "Find and replace"
        message = "Enter string to remove"
        stringToRemove = tkSimpleDialog.askstring(title,message)
        if(stringToRemove == None): return
        message = "Enter string to add"
        stringToReplace = tkSimpleDialog.askstring(title, message)
        if(stringToReplace == None): return
        self.currentText = self.currentText.replace(
            stringToRemove, stringToReplace)
        self.textWidget.delete(1.0, END)
        self.textWidget.insert(1.0, self.currentText)
        self.highlightString(stringToReplace)

    def initTextWidget(self):
        # initialises text widget
        # used the below link to make it stop resizing on font change
        # http://stackoverflow.com/questions/9833698/
        # python-tkinter-how-to-stop-text-box-re-size-on-font-change
        self.textWidgetContainer = Frame(self.root, borderwidth = 1,
            relief = "sunken", width = 600, height = 400)
        self.textWidgetContainer.grid_propagate(False)
        self.textWidgetContainer.pack(side = TOP, fill = "both", expand = True)
        self.textWidgetContainer.grid_rowconfigure(0, weight=1)
        self.textWidgetContainer.grid_columnconfigure(0, weight=1)
        self.textWidget = ScrolledText(self.textWidgetContainer, 
            width = 10,
            font = self.font,
            background =self.textWidgetBackGround)
        self.textWidget.grid(row = 0, column = 0, sticky = "nsew")
        self.textWidget.config(insertbackground = self.cursorColor,
            foreground = self.textWidgetDefaultFontColor,
            tabs = ("%dc"%self.tabWidth,"%dc"%(2*self.tabWidth)),
            undo = True)

    def initFont(self):
        self.currentFont = "Arial"
        self.fontSize = 15
        self.font = tkFont.Font(family = self.currentFont, 
            size = self.fontSize)

    def initProgrammingModeAttributes(self):
        self.programmingMode = False
        self.errorDetectionMode = False
        self.colorScheme = None
        self.defaultColorScheme = "monokai"
        self.lexer = None

    def initMoreGeneralAttributes(self):
        self.hostingServer = False
        self.hostIP = None
        self.joinedServerIP = None
        self.server = None
        self.client = None
        self.spellCorrector = SpellCorrector()
        self.root.wm_title("Untitled")
        self.commentButX = self.width - 300
        self.commentButY = 10
        self.commentButWidth = 200
        self.commentButHeight = self.height - 10

    def initGeneralAttributes(self):
        # general editor attributes
        self.currentText,self.tabWidth = "",1
        self.rulerWidth,self.currentFilePath = None,None
        self.currentFile = None
        self.fileExtension = None
        self.suggestionDict = dict()
        self.indentationLevel = 0
        self.prevChar = None
        self.spellCorrection = False
        self.clipboard = ""
        self.comments = ["comments"]
        self.collaborativeCodingMode = False
        self.insertColor = "Black"
        self.initMoreGeneralAttributes()

    def initTextWidgetAttributes(self):
        self.textWidgetBackGround = "White"
        self.textWidgetDefaultFontColor = "Black"
        self.textWidgetTabSize = ""
        self.cursorColor = "Black"

    def initAttributes(self):
        self.initGeneralAttributes()
        self.initFont()
        self.initProgrammingModeAttributes()
        self.initTextWidgetAttributes()

    def addEditMenu(self):
        self.editMenu = Menu(self.menuBar, tearoff = 0)
        self.editMenu.add_command(label = "Undo", command = self.undo)
        self.editMenu.add_command(label = "Redo", command = self.redo)
        self.editMenu.add_command(label = "Cut", command = self.cut)
        self.editMenu.add_command(label = "Copy", command = self.copy)
        self.editMenu.add_command(label = "Paste", command = self.paste)
        self.editMenu.add_command(label = "Increase Font", 
            command = self.increaseFontSize)
        self.editMenu.add_command(label = "Decrease Font", 
            command = self.decreaseFontSize)
        self.menuBar.add_cascade(label = "Edit", menu = self.editMenu)

    def addFileMenu(self):
        self.fileMenu = Menu(self.menuBar, tearoff = 0)
        self.fileMenu.add_command(label = "Open", command = self.openFile)
        self.fileMenu.add_command(label = "New File", command = self.newTab)
        self.fileMenu.add_command(label = "Save", command = self.saveFile)
        self.fileMenu.add_command(label = "Save As", command = self.saveAs)
        self.menuBar.add_cascade(label = "File", menu = self.fileMenu)

    def setFileExtension(self, ext):
        # sets file extension
        self.fileExtension = ext
        self.programmingMode = True
        try:
            self.lexer = pygments.lexers.guess_lexer_for_filename("example%s"%self.fileExtension,[])
        except:
            self.lexer = pygments.lexers.guess_lexer_for_filename("example.py",[])
        self.highlightText()

    def setColorScheme(self, colorScheme):
        self.colorScheme = colorScheme
        self.programmingMode = True
        # assumes start from python
        if(not self.lexer):
            self.lexer = pygments.lexers.guess_lexer_for_filename("example.py",[])
            self.fileExtension = ".py"
        self.highlightText()

    # should have radio buttons for this
    def turnOnErrorDetection(self):
        self.errorDetectionMode = True
        self.setFileExtension(".py")

    def turnOffErrorDetection(self):
        self.errorDetectionMode = False

    def turnOnSpellCorrection(self):
        self.spellCorrection = True

    def turnOffSpellCorrection(self):
        self.spellCorrection = False

    def addErrorDetectionMenu(self):
        self.errorDetectionMenu = Menu(self.menuBar, tearoff = 0)
        self.errorDetectionMenu.add_command(label = "Python error detection ON",
            command = self.turnOnErrorDetection)
        self.errorDetectionMenu.add_command(label = "Python error detection OFF",
            command = self.turnOffErrorDetection)
        self.viewMenu.add_cascade(label = "Error Detection",
            menu = self.errorDetectionMenu)

    def addSpellCorrectionMenu(self):
        self.spellCorrectionMenu = Menu(self.menuBar, tearoff = 0)
        self.spellCorrectionMenu.add_command(label = "Spelling Correction ON",
            command = self.turnOnSpellCorrection)
        self.spellCorrectionMenu.add_command(label = "Spelling Correction OFF",
            command = self.turnOffSpellCorrection)
        self.viewMenu.add_cascade(label = "Spelling Correction",
            menu = self.spellCorrectionMenu)

    def addColorSchemeCommand(self, name):
        self.colorSchemeMenu.add_command(label = name,
                command = lambda : self.setColorScheme(name))

    def addColorSchemeMenu(self):
        # colorScheme Menu
        self.colorSchemeMenu = Menu(self.menuBar, tearoff = 0)
        self.addColorSchemeCommand("manni")
        self.addColorSchemeCommand("igor")
        self.addColorSchemeCommand("xcode")
        self.addColorSchemeCommand("vim")
        self.addColorSchemeCommand("autumn")
        self.addColorSchemeCommand("vs")
        self.addColorSchemeCommand("rrt")
        self.addColorSchemeCommand("native")
        self.addColorSchemeCommand("perldoc")
        self.addColorSchemeCommand("borland")
        self.addColorSchemeCommand("tango")
        self.addColorSchemeCommand("emacs")
        self.addColorSchemeCommand("friendly")
        self.addColorSchemeCommand("monokai")
        self.addColorSchemeCommand("paraiso-dark")
        self.addColorSchemeCommand("colorful")
        self.addColorSchemeCommand("murphy")
        self.addColorSchemeCommand("bw")
        self.addColorSchemeCommand("pastie")
        self.addColorSchemeCommand("paraiso-light")
        self.addColorSchemeCommand("trac")
        self.addColorSchemeCommand("default")
        self.addColorSchemeCommand("fruity")
        self.menuBar.add_cascade(label = "Color Scheme",
            menu = self.colorSchemeMenu)

    def addLanguageCommand(self, language, extension):
        self.syntaxMenu.add_command(label = language, 
            command = lambda : self.setFileExtension(extension))

    def addSyntaxMenu(self):
        self.syntaxMenu = Menu(self.menuBar, tearoff = 0)
        self.addLanguageCommand("Python",".py")
        self.addLanguageCommand("C++",".cpp")
        self.addLanguageCommand("Javascript",".js")
        self.addLanguageCommand("Java",".java")
        self.addLanguageCommand("HTML",".html")
        self.addLanguageCommand("CSS",".css")
        self.addLanguageCommand("PHP",".php")
        self.addLanguageCommand("Haskell",".hs")
        self.addLanguageCommand("Clojure",".clj")
        self.addLanguageCommand("CoffeeScript",".coffee")
        self.addLanguageCommand("AppleScript",".scpt")
        self.addLanguageCommand("Objective C",".h")
        self.addLanguageCommand("Scheme",".scm")
        self.addLanguageCommand("Ruby",".rb")
        self.addLanguageCommand("OCaml",".ml")
        self.addLanguageCommand("Scala",".scala")
        self.viewMenu.add_cascade(label = "Syntax", menu = self.syntaxMenu)
        self.menuBar.add_cascade(label = "View", menu = self.viewMenu)

    def addViewMenu(self):
        self.viewMenu = Menu(self.menuBar, tearoff = 0)
        # syntax Menu
        self.addSyntaxMenu()
        self.addColorSchemeMenu()
        self.addErrorDetectionMenu()
        self.addSpellCorrectionMenu()

    def displayMessageBox(self, title = "", text = ""):
        tkMessageBox.showinfo(title, text)

    def startServer(self):
        # starts a new thread running the server
        self.collaborativeCodingMode = True
        start_new_thread(self.server.acceptConnection(),())

    def startRecieving(self):    
        # starts a new thread to recieve data
        start_new_thread(self.client.recieveData,())

    def collaborateWrapper(self):
        # starts collaborative mode
        if(not self.collaborativeCodingMode):
            self.server = Server()
            host = self.server.getHost()
            self.hostingServer = True
            self.hostIP = host
            self.client = Client(host)
            start_new_thread(self.startServer,())
            start_new_thread(self.startRecieving,())
            self.client.sendData(";".join(self.comments))
            time.sleep(.01)
            self.client.sendData(self.currentText)

    def joinServer(self):
        # starts a new thread to recieve data
        start_new_thread(self.client.recieveData,())

    def joinServerWrapper(self):
        # join a server for collaboration
        if(not self.collaborativeCodingMode):
            try:
                self.collaborativeCodingMode = True
                title = "Host IP address"
                message = "Enter IP address of server to link to."
                host = tkSimpleDialog.askstring(title,message)
                if(host == None): 
                    self.collaborativeCodingMode = False
                    return       
                self.joinedServerIP = host
                self.client = Client(host)
                start_new_thread(self.joinServer,())
            except:
                self.collaborativeCodingMode = False
                self.joinedServerIP = None
                print "Server isn't running"
                self.displayMessageBox("Error","Server isn't running")

    def addNetworkMenu(self):
        self.networkMenu = Menu(self.menuBar, tearoff = 0)
        self.networkMenu.add_command(label = "Collaborate| Create new server", 
                                    command = self.collaborateWrapper)
        self.networkMenu.add_command(label = "Collaborate| Join server", 
                                    command = self.joinServerWrapper)
        self.menuBar.add_cascade(label = "Collaborative", 
                                menu = self.networkMenu)
        
    def addFindMenu(self):
        self.findMenu = Menu(self.menuBar, tearoff = 0)
        self.findMenu.add_command(label = "Search", command =self.searchInText)
        self.findMenu.add_command(label = "Find and Replace", 
            command = self.findAndReplaceInText)
        self.menuBar.add_cascade(label = "Find", menu = self.findMenu)

    def showHelp(self):
        self.helpCanvasRoot = Tk()
        self.helpCanvas = Canvas(self.helpCanvasRoot, width = 600, height = 600)
        self.helpCanvasRoot.wm_title("Collaborative Coder | Help")
        self.helpCanvas.pack()
        canvas = self.helpCanvas
        canvas.create_rectangle(0,0,600,600,fill="Grey")
        canvas.create_text(300,30,text = "Collaborative Coder!", 
            font = "Arial 30 bold italic underline")
        canvas.create_rectangle(8,48,592,596,fill = "White",
            width = 2)
        message = """
        1. Find all options on the top of the screen in the menu bar.
        2. There are two boxes on the screen which hold 
            comments and suggestions(Autocomplete and
            Spelling Correction) respectively.
            To choose a suggestion double click on it.
        3. To enable syntax highlighting choose the programming 
            language in View --> Syntax menu.
        4. Choose the color scheme you want in the color
            scheme menu.
        5. Press Command+B to compile python code.
        6. Turn on or off dynamic python error detection and 
           spelling correction from view menu.
        7. To collaborate with others you can either start a server
            or join a server
                1. To start a server click 
                    Collaboration --> Start New Server
                    This will display your IP address in the 
                    bottom which your friend will join.
                2. To join click Collaboration --> Join Server
                    Enter server IP you want to join
                    and click OK.
        8. To annotate select a piece of text and press 
            the comment button in the bottom right. When your cursor
            shows up in those indices the annotation will show
            up in the comments box.

        """
        canvas.create_text(10,50,text = message, anchor = "nw",
            fill = "Dark Blue", font = "Arial 18 bold")
        canvas.mainloop()

    def showAbout(self):
        self.aboutCanvasRoot = Tk()
        self.aboutCanvas = Canvas(self.aboutCanvasRoot, width = 600,height =670)
        self.aboutCanvasRoot.wm_title("Collaborative Coder | About")
        self.aboutCanvas.pack()
        self.aboutCanvas.create_rectangle(0,0,600,670,fill="Grey")
        self.aboutCanvas.create_text(300,30,text = "Collaborative Coder!", 
            font = "Arial 30 bold italic underline")
        self.aboutCanvas.create_rectangle(8,48,592,652,fill = "White",
            width = 2)
        message = """
        This is a text editor application made by Manik Panwar
        for the course 15-112 Fundamentals of programming and 
        computer science at Carnegie Mellon University,
        which you can use to edit text documents and write code.
        Not only can you do this on your own
        machine but you can also collaborate 
        with friends live on different computers 
        through the internet and edit the same 
        text documents; all the while commenting 
        and annotating the text which automatically 
        shows up on your friends computer.
        Apart from all the general text editor features 
        this also supports syntax highlighting for 
        all major languages, autocompletion(which show up 
        in the suggestion box), autoindenation,
        auto parentheses completion, spelling correction,
        dynamic python error detection, multiple text editor 
        color schemes and live collaboration with 
        others on other machines. For collaborating with 
        a friend you can either create a server and ask 
        your friends to join your server or
        join an already running server. All you have to 
        do now is choose a language from the syntax menu, 
        choose your color scheme and preferences, set up 
        collaboration with a friend, and get started on 
        that 15-112 inspired project you are now about to do!
        """
        self.aboutCanvas.create_text(10,50,text = message, anchor = "nw",
            fill = "Dark Blue", font = "Arial 18 bold")
        self.aboutCanvasRoot.mainloop()

    def addHelpMenu(self):
        self.helpMenu = Menu(self.menuBar, tearoff = 0)
        self.helpMenu.add_command(label = "Help", command = self.showHelp)
        self.helpMenu.add_command(label = "About", command = self.showAbout)
        self.menuBar.add_cascade(label = "Help", menu = self.helpMenu)

    def initListBox(self):
        self.suggestionBox = Listbox(self.root, width = 50,
                    height = 5,selectmode = SINGLE)
        self.scrollbar = Scrollbar(self.root, orient = VERTICAL)
        self.scrollbar.config(command = self.suggestionBox.yview)
        self.scrollbar.pack(side = RIGHT,fill = Y)
        self.suggestionBox.config(yscrollcommand = self.scrollbar.set,
            background = "Grey")
        self.suggestionBox.pack(side = RIGHT)
        self.suggestionBox.insert(END, "Suggestions(Autocomplete and Spelling correction):")

    def initCommentBox(self):
        self.commentBoxFontSize = 20
        self.commentBox = Listbox(self.root, width = 180,height = 5, 
                                    selectmode = SINGLE)
        self.commentScrollbar = Scrollbar(self.root, orient = VERTICAL)
        self.commentScrollbar.config(command = self.commentBox.yview)
        self.commentScrollbar.pack(side = RIGHT,fill = Y)
        self.commentBoxFont = tkFont.Font(family = self.currentFont,
            size = self.commentBoxFontSize)
        self.commentBox.config(yscrollcommand = self.commentScrollbar.set,
            background = "Grey", foreground = "Black",
            font = self.commentBoxFont)
        self.commentBox.pack(side = RIGHT, fill = X)
        self.commentBox.insert(END,"Comments (if any) in current cursor index:")

    def initMenuBar(self):
        # init menuBar
        self.menuBar = Menu(self.root)
        # file menu option
        self.addFileMenu()
        # Edit menu option
        self.addEditMenu()
        # Find menu option
        self.addFindMenu()
        # View menu option
        self.addViewMenu()
        # Network menu
        self.addNetworkMenu()
        # Help menu
        self.addHelpMenu()
        self.root.config(menu = self.menuBar)

    def onTabPressed(self, event):
        if(self.fileExtension == ".py"):
            self.indentationLevel += 1

    def bindEvents(self):
        self.textWidget.bind("<Tab>",lambda event: self.onTabPressed(event))
        self.suggestionBox.bind("<Double-Button-1>", 
                                lambda event: self.replaceWord(event))

    def indent(self):
        if(self.fileExtension == ".py"):
            self.textWidget.insert("insert","\t"*self.indentationLevel)

    def modifyIndent(self, event):
        # modifies indentation based on python rules
        if(self.fileExtension == ".py"):
            if(event.char == ":"): 
                self.indentationLevel += 1
            elif(event.keysym == "BackSpace"):
                line = self.textWidget.get("insert linestart","insert lineend")
                flag = True
                for c in line:
                    if not((c == " ") or (c == "\t")):
                        flag = False
                        break
                if(flag):
                    self.indentationLevel = (self.indentationLevel - 1 if 
                        self.indentationLevel>=1 else 0)

    def completeParens(self, event):
        # autocomplete parens
        if(event.char == "{" and self.programmingMode):
            self.textWidget.insert("insert","\n"+"\t"*self.indentationLevel+"}")
            self.currentText = self.textWidget.get(1.0,END)
        elif(event.char == "(" and self.programmingMode):
            self.textWidget.insert("insert",")")
            self.currentText = self.textWidget.get(1.0,END)

    def replaceWord(self,event):
        # replaces a word on double click in suggestion box
        word = self.getCurrentWord()
        self.textWidget.delete("insert - %dc"%(len(word)),"insert")
        wordToReplace = ""
        if(self.suggestionBox.curselection()):
            wordToReplace = self.suggestionBox.get(
                            self.suggestionBox.curselection())
            if(wordToReplace != "Suggestions(Autocomplete and Spelling correction):"):
                self.textWidget.insert("insert", wordToReplace)
            self.resetSuggestions()

    def calculateSuggestions(self):
        # populates suggestion box
        self.suggestionBox.delete(0,END)
        self.suggestionDict = dict()
        currentWord = self.getCurrentWord()
        self.findMatchesToWord(currentWord)
        self.suggestionBox.insert(END,
            "Suggestions(Autocomplete and Spelling correction):")
        for key in self.suggestionDict:
            self.suggestionBox.insert(END,key)
        if(self.spellCorrection):
            correctSpelling = self.spellCorrector.correct(currentWord)
            if(not currentWord.startswith(correctSpelling)):
                self.suggestionBox.insert(END, correctSpelling)

    def resetSuggestions(self):
        self.suggestionBox.delete(0,END)
        self.suggestionBox.insert(END, 
            "Suggestions(Autocomplete and Spelling correction):")
        self.suggestionDict = dict()

    def compilePythonCode(self):
        if(self.currentFile):
            self.saveFile()
            original_stdout = sys.stdout
            try:
                a = compiler.compile(self.currentText, self.currentFile, 
                                    mode = "exec")
                # (http://stackoverflow.com/questions/4904079/
                # execute-a-block-of-python-code-with-exec-capturing-all-its-output)
                # captures stdout in temp stringIO buffer to get output
                # and then reverts changes
                buffer = StringIO()
                sys.stdout = buffer
                eval(a)
                sys.stdout = original_stdout
                val = buffer.getvalue()
                rt = Tk()
                outputText = ScrolledText(rt, width = 50)
                outputText.insert(END, val)
                outputText.pack()
                rt.mainloop()
            except:
                print "Error!"
                self.displayMessageBox("Error","There is an error in the code.")
                sys.stdout = original_stdout
        else:
            self.saveAs()

    def getLineAndColFromIndex(self, index):
        return int(index.split('.')[0]),int(index.split('.')[1])

    def checkIfInCommonRange(self, comment):
        # check if insert is in range of any comment
        index = self.textWidget.index("insert")
        indexCStart = comment[0]
        indexCEnd = comment[1]
        line,col = self.getLineAndColFromIndex(index)
        line1,col1 = self.getLineAndColFromIndex(indexCStart)
        line2,col2 = self.getLineAndColFromIndex(indexCEnd)
        if((line>line1 and line<line2) or
            (line == line1 and col>=col1 and (line1!=line2 or col<=col2)) or 
            (line == line2 and col<=col2 and (line1!=line2 or col>=col1))):
            return True
        else:
            return False

    def checkComments(self):
        self.commentBox.delete(0,END)
        self.commentBox.insert(END,"Comments (if any) in current cursor index:")
        for comment in self.comments:
            if("|" in comment):
                comment = comment.split("|")
                if(self.checkIfInCommonRange(comment)):
                    self.commentBox.insert(END, comment[2])

    def onKeyPressed(self, event):
        ctrl  = ((event.state & 0x0004) != 0)
        shift = ((event.state & 0x0001) != 0)
        command = ((event.state & 0x0008) != 0)
        flag = False
        self.checkComments()
        if(self.textWidget.get(1.0,END)!=self.currentText):
            flag = True
        if(event.char.isalpha()):
            self.calculateSuggestions()
        if(event.keysym == "Return" and self.fileExtension == ".py"):
            self.indent()
        if(event.keysym in ["Return"," ","\n","\t","BackSpace","space"]):
            self.resetSuggestions()
        self.currentText = self.textWidget.get(1.0,END)
        self.modifyIndent(event)
        self.completeParens(event)
        if((flag) and self.collaborativeCodingMode):
            self.client.sendData(self.currentText)
        if(self.programmingMode):
            if((command and event.keysym in "vV")):
                self.highlightText()
            else:
                insertLineNumber = int(self.textWidget.index(
                                                    "insert").split(".")[0])
                self.highlightText(
                        str(insertLineNumber),"0", 
                        (event.keysym!="Return" and 
                        not self.collaborativeCodingMode)
                        ) 
        if(self.fileExtension == ".py" and command and event.keysym in "bB"):
            self.compilePythonCode()

    def onMousePressed(self, event):
        # remove search tag if it exists
        self.textWidget.tag_delete("search")
        self.checkComments()
        if((event.x>=self.commentButX) and 
            (event.x<=(self.commentButX + self.commentButWidth)) and
            (event.y>=self.commentButY) and 
            (event.y<=(self.commentButY + self.commentButHeight))):
            self.commentCode()

    def onTimerFired(self):
        pass

    def redrawAll(self):
        # draws info onto canvas
        self.canvas.delete(ALL)
        self.canvas.create_rectangle(0,0,self.width,self.height,fill = "Black")
        self.canvas.create_rectangle(self.commentButX,self.commentButY,
            self.commentButX+self.commentButWidth,
            self.commentButY+self.commentButHeight,fill = "Grey")
        self.canvas.create_text(self.commentButX + self.commentButWidth/2,
            self.commentButY + self.commentButHeight/2,text = "Comment")
        self.canvas.create_text(400,10,
            text = "Press help in the menu bar to get started", fill = "White")
        if(self.programmingMode):
            self.canvas.create_text(600,10,
                            text = "Programming mode on",fill="Green")
        if(self.errorDetectionMode):
            self.canvas.create_text(600,25,
                            text = "Error detection mode on",fill = "Green")
        if(self.spellCorrection):
            self.canvas.create_text(600,40,
                            text = "Spelling Correction on",fill = "Green")
        a = self.textWidget.index("insert")
        ln = int(a.split(".")[0])
        l = self.textWidget.get("insert linestart","insert")
        cn = 1
        for c in l:
            if(c == "\t"):
                cn += 4*self.tabWidth
            else:
                cn += 1
        self.canvas.create_text(100,10,text="Row:%d Column:%d"%(ln,cn),
                                fill = "White")
        self.canvas.create_text(850,30,text = "Collaborative Coder!",
            fill = "Grey", font = "Arial 30 bold")
        if(self.hostingServer):
            self.canvas.create_text(400,30,
                text = "Hosting server at IP: %s"%(self.hostIP),fill="White")
        elif(self.joinedServerIP):
            self.canvas.create_text(400,30,
                text = "Joined server at IP: %s"%(self.joinedServerIP),
                fill = "White")


    def initAnimation(self):
        self.timerCounter = 10000
        self.initAttributes()
        self.initTextWidget()
        self.initMenuBar()
        self.initListBox()
        self.initCommentBox()
        self.bindEvents()

t = TextEditor(1500,50)

class Server(object):
    def __init__(self,port = 5555):
        # self.host = '127.0.0.1'  # '' means connect to all hosts
        self.port = port
        self.text = ""      
        self.host = socket.gethostbyname(socket.gethostname())
        print self.host," is host" 
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.s.bind((self.host, self.port))
        except socket.error as e:
            print(str(e))
        self.s.listen(2)
        self.connections = []

    def getHost(self):
        return self.host

    def threaded_client(self,conn):
        # conn.send("Connected to server\n")
        while True:
            try:
                data = conn.recv(2048)
            except:
                data = ""
            if(not data):
                break
            # conn.sendall(reply)
            for c,a in self.connections:
                try:
                    c.sendall(data)
                except:
                    print "connection lost"
                    self.connections.remove((c,a))
        conn.close()

    def acceptConnection(self):
        while True:
            conn, addr = self.s.accept()
            self.connections += [(conn,addr)]
            start_new_thread(self.threaded_client,(conn,))
    
class Client(object):
    def __init__(self,host = '127.0.0.1',name = "user"):
        self.host = host
        self.port = 5555
        self.name = name
        self.client= socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        self.client.connect((self.host,self.port))
        self.text = ""
        self.l = threading.Lock()

    def sendData(self,data):
        self.client.send(data)

    def recieveData(self):
        while True:
            try:
                data = self.client.recv(8192)
            except:
                break
            if data:
                self.l.acquire()
                self.text = data
                self.l.release()
                if(not data.startswith("comments")):
                    index = t.textWidget.index("insert")
                    t.textWidget.delete(1.0,END)
                    t.textWidget.insert(END, self.text[:-1])
                    t.textWidget.mark_set('insert',index)
                    if(t.programmingMode):
                        t.highlightText()
                else:
                    t.comments = data.split(";")
        self.client.close()

    def data(self):
        self.l.acquire()
        ret = self.text
        self.l.release()
        return ret

    def closeClient(self):
        self.client.close()


class MyParse(object):
    def pythonCodeContainsErrorOnParse(self, code):
        flag = False
        ls = []
        try:
            compiler.parse(code, mode = "exec")
        except Exception as e:
            flag = True
            # traceback.print_exc()
            s = traceback.format_exc()
            ls = s.split("\n")
        return flag,ls

    def pythonCodeContainsErrorOnCompile(self, code):
        flag = False
        ls = []
        try:
            compiler.compile(code,"file.py", mode = "exec")
        except Exception as e:
            flag = True
            s = traceback.format_exc()
            ls = s.split("\n")
        return flag,ls

# based on http://norvig.com/spell-correct.html

# modify to return multiple words all of which have same probability?

class SpellCorrector(object):

    @staticmethod
    def readFile(filename, mode="rt"):
        # From 15-112 class notes
        # rt = "read text"
        with open(filename, mode) as fin:
            return fin.read()

    def trainModel(self, data):
        model = collections.defaultdict(lambda : 1)
        for word in data:
            model[word] += 1
        return model

    def getWords(self, data):
        return set(re.findall('[a-z]+',  data.lower()))

    def edit_distance_of_one(self, word):
        splits = [(word[:i],word[i:]) for i in xrange(len(word)+1)]
        deletions = [a + b[1:] for a,b in splits if b]
        insertions=[a + c + b for a,b in splits for c in string.ascii_lowercase]
        transposes = [a + b[1] + b[0] + b[2:] for a,b in splits if len(b)>1]
        replaces=[a + c + b[1:] for a, b in splits for c in string.ascii_lowercase if b]
        return set(deletions+insertions+transposes+replaces)

    def edit_distance_of_two(self, word):
        return set(w2 for w1 in self.edit_distance_of_one(word) 
            for w2 in self.edit_distance_of_one(w1) if w2 in self.allWords)

    def known(self, words):
        return set(w for w in words if w in self.allWords)

    def __init__(self):
        data = SpellCorrector.readFile('trainingWords.rtf')
        t = time.time()
        self.allWords = self.trainModel(self.getWords(data))
        # could possibly save this on a txt so I don't have to do this everytime

    def correct(self,word):
        possibleWords = (self.known([word]) or 
            self.known(self.edit_distance_of_one(word)) or 
            self.known(self.edit_distance_of_two(word)) or [word])
        return max(possibleWords, key = self.allWords.get) 


def test(corrector, word):
    t = time.time()
    print "%s --> %s"%(word,corrector.correct(word))
    print "Time taken for %s:%f"%(word,(time.time()-t)*1000)

def testSpellCorrector():
    corrector = SpellCorrector()
    test(corrector, "correcto")
    test(corrector, "korrector")
    test(corrector, "remembe")
    test(corrector, "saty")
    test(corrector, "brav")
    test(corrector, "functio")
    test(corrector, "functiok")
    test(corrector, "funktioc")
    test(corrector, "dictionayu")

t.run()

