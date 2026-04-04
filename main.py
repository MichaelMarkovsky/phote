from features.raw_processing import load_raw_image
from features.perspective import detect_document, warp
import cv2 as cv
import os
from pathlib import Path
import shutil

from textual.app import App
from textual.widgets import Footer,Static
from textual.widgets import Tree

from textual.containers import Container, Horizontal, VerticalScroll

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
    CSS_PATH = "styles.tcss"

    BINDINGS = [
        #(key, action name, description),

        ("q", "quit" , "Exit the application")
            ]

    def compose(self):
        self.status = Static("Ready")
        self.photo_tree = self.photo_list()
        
        with Container(id="app-grid"):
             with VerticalScroll(id="left-pane"):
                yield self.photo_tree
             with Horizontal(id="right-pane"):
                yield Static("Preview",id="preview")
        # Widgets
        yield self.status
        yield Footer()


    def on_mount(self):
        files = get_photos(".")
        self.status.update(f"Found {len(files)} files")

        # Focus on the tree when the app starts
        self.set_focus(self.photo_tree)


    def photo_list(self):
        tree: Tree[str] = Tree("Files", classes="photo_tree")
        
        tree.show_root = False

        base_path = os.path.abspath(".")

        for file in get_photos(base_path):
            full_path = os.path.join(base_path, file)

            tree.root.add_leaf(file, data=full_path)

        return tree

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted) -> None:
        path = event.node.data

        if not path:
            return

        # Create tmp folder if not exists
        folder_path = Path("./temp")
        # exist_ok=True: does nothing if the folder already exists
        folder_path.mkdir(exist_ok=True)

        img = load_raw_image(path)
        cv.imwrite('./temp/preview.jpg', img)


  
    # This is an action method. (name starts with action)
    # When i press q i then shutdown and exit the program
    def action_quit(self):
        # Delete the temp folder
        temp_dir = "./temp"

        if os.path.isdir(temp_dir):  
            shutil.rmtree(temp_dir)

        self.exit()



if __name__ == "__main__":
    phote().run()
