from features.raw_processing import load_raw_image
from features.perspective import detect_document, warp
import cv2 as cv
import os

from textual.app import App
from textual.widgets import Footer,Static
from textual.widgets import Tree


# ---------- LOAD ----------
#img = load_raw_image("IMG_9095.CR3")

# ---------- DETECT ----------
#pts = detect_document(img)

# ---------- WARP ----------
#warped = warp(img, pts)

# ---------- SHOW ----------
#cv.imwrite("preview.png", warped)

#os.system("kitty +kitten icat --clear")
#os.system("kitty +kitten icat preview.png")



# Get the list of all files and directories
def get_photos(path):
        raw_files = []

        for x in os.listdir(path):
            if x.lower().endswith(".cr3"):
                raw_files.append(x) 

        return raw_files





class phote(App):
    BINDINGS = [
        #(key, action name, description),

        ("q", "quit" , "Exit the application")
            ]

    def compose(self):
        self.status = Static("Ready")
        self.photo_tree = self.photo_list()

        # Widgets
        yield self.photo_tree
        yield self.status
        yield Footer()


    def on_mount(self):
        files = get_photos(".")
        self.status.update(f"Found {len(files)} files")


    def photo_list(self):
        tree: Tree[str] = Tree("Files")
        
        tree.show_root = False

        files = get_photos(".")

        for file in files:
            tree.root.add_leaf(file)

        return tree


        # This is an action method. (name starts with action)
    def action_quit(self):
        self.log("Quitting app")
        self.exit()



if __name__ == "__main__":
    phote().run()
