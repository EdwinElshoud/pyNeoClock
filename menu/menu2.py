import helpers

ButtonCode = helpers.enum(ESCAPE=1, UP=2, DOWN=3, LEFT=4, RIGHT=5)
MenuState = helpers.enum(DISABLED=0, IN_MENU=1, IN_CALLBACK=2, EXIT=3)


class MenuItem:
    def __init__(self, name, on_enter=None, on_process=None, on_exit=None, kwargs=None):
        self._name = name
        self._on_enter = on_enter
        self._on_process = on_process
        self._on_exit = on_exit
        self._kwargs = kwargs
        self._children = {}
        
    def show_menu_struct(self, level):
        offset = "  " * level
        print(f"{offset}- {self._name} [child count={len(self._children)}]")
        
        for k in self._children:
            self._children[k].show_menu_struct(level+1)
            
    def name(self):
        return self._name
    
    def is_leaf(self):
        return len(self._children) == 0
    
    def add_child(self, child_menu_item):
        self._children.append(child_menu_item)
    
    def get_child_by_name(self, child_name):
        if child_name not in self._children:
            print(f"Faild to find child: {child_name}")
            return None
        
        return self._children[child_name]
    
    def get_child_by_index(self, index):
        if len(self._children) == 0 or index >= len(self._children):
            print(f"Invalid index to child or no children: {index}")
            return None
        
        # Create a list with all the key values of the children
        submenu_items = list(self._children.keys())
        return self._children[submenu_items[index]]
    
    def children(self):
        return self._children
    
    def on_enter(self, **kwargs):
        # Execute the callback function when menu item is entered
        # Join the parameter kwargs with the objects default kwargs
        print(f"{self._name}::on_enter")
        if self._on_enter is not None:
            args = {}
            
            if kwargs:
                args.update(kwargs)
            if self._kwargs:
                args.update(self._kwargs)
            print(f"kwargs={kwargs}")
            print(f"{self._kwargs}")
            print(f"args={args}")
            self._on_enter(**self._kwargs)

    def on_exit(self, **kwargs):
        # Execute the callback function when menu item is exited
        print(f"{self._name}::on_exit")
        if self._on_exit is not None:
            args = {}
            
            if kwargs:
                args.update(kwargs)
            if self._kwargs:
                args.update(self._kwargs)

            self._on_exit(**args)
    
    def on_process(self, **kwargs):
        # Execute the callback
        print(f"{self._name}::on_process")

        if self._on_process is not None:
            args = {}
            
            if kwargs:
                args.update(kwargs)
            if self._kwargs:
                args.update(self._kwargs)

            self._on_process(**args)
            
        
class Menu:
    def __init__(self):
        self._main_menu = {"*MENU*": MenuItem("menu"),}
        self._breadcrums = []
        self._current_menu_item = None
        self.add_menu_item(["exit"])
        self._breadcrums = ["*MENU*"]
        self._submenu_index = 0
        self._state = MenuState.DISABLED

    def show_menu_struct(self):
        print(len(self._main_menu))
        level = 0          
        for k in self._main_menu:
            #print(k)
            self._main_menu[k].show_menu_struct(level+1)
        
    def show_breadcrums(self):
        print(self._breadcrums)
        
    def start(self):
        submenu_items = list(self._main_menu["*MENU*"].children().keys())
        #self._breadcrums.append(submenu_items[0])
        self._submenu_index = 0
        self._state = MenuState.IN_MENU

    def menu_text(self):
        active_menu_item = self._get_current_menu_item(self._breadcrums)
        if active_menu_item.is_leaf(): 
            return None
        
        return active_menu_item.get_child_by_index(self._submenu_index).name()
                                                       
    def add_menu_item(self, menu_path, on_enter=None, on_process=None, on_exit=None, kwargs=None):
        leaf_element = menu_path.pop()
        childlist = self._main_menu["*MENU*"].children()
        
        for i in menu_path:
            if i not in childlist:
                # menu element in the menu path does not exist yet
                childlist[i] = MenuItem(i, None, None, None)
            childlist = childlist[i].children()
            
        childlist[leaf_element] = MenuItem(leaf_element, on_enter, on_process, on_exit, kwargs)

    def _get_current_menu_item(self, breadcrum):
        """
        :param breadcrum: list of elements in the menu to traverse

        :return: sub dict of the menu
        """
        #print(f"Traversing breadcrums: {breadcrum}")
        #print(f"submenu_index : {self._submenu_index}")
        menu_item = self._main_menu["*MENU*"]
        for i in breadcrum:
            if i == "*MENU*":
                continue
            
            #print(f"Entering {i}")
            menu_item = menu_item.get_child_by_name(i)
        return menu_item
        
    def button_event(self, button, event):
        active_menu = self._get_current_menu_item(self._breadcrums)
        print(active_menu)
        if isinstance(active_menu, MenuItem) and active_menu.is_leaf():
            # Pass onto handling button events whan on a leaf
            return self._button_event_leaf(active_menu, button, event)
        else:
            return self._button_event_traverse(active_menu, button, event)
        
    def _button_event_leaf(self, active_menu, button, event):
        kwargs = {"button": button, "event": event}
        if button != ButtonCode.ESCAPE:
            active_menu.on_process(**kwargs)
            self._state = MenuState.IN_CALLBACK
        else:
            # Call the on_exit callback and remove last element from breadcrums
            active_menu.on_exit()
            self._breadcrums.pop()
            self._submenu_index = 0
            self._state = MenuState.IN_MENU
            
        return self._state
    
    def _button_event_traverse(self, active_menu, button, event):
        # Process button event to traverse through menu
        submenu_items = list(active_menu.children().keys())
        print(f"submenu items = {submenu_items}")
        if button == ButtonCode.DOWN:
            print("Button DOWN")
            self._submenu_index += 1
            if self._submenu_index >= len(submenu_items):
                self._submenu_index = 0
            print(f"  --> {submenu_items[self._submenu_index]}")
                
        elif button == ButtonCode.UP:
            print("Button UP")
            if self._submenu_index > 0:
                self._submenu_index -= 1

            print(f"  --> {submenu_items[self._submenu_index]}")
                
        elif button == ButtonCode.RIGHT:
            print("Button RIGHT")
            # Go deeper into the menu structure and add the submenu name to the breadcrums
            submenu_name = submenu_items[self._submenu_index]
            if submenu_name == "exit":
                self._state = MenuState.EXIT
            else:
                self._breadcrums.append(submenu_name)
                new_active_menu_item = self._get_current_menu_item(self._breadcrums)
                # Execute the on_enter callback (if defined)
                kwargs = {"button": button, "event": event}
                new_active_menu_item.on_enter(**kwargs)
                self._submenu_index = 0
            
        elif button == ButtonCode.LEFT:
            # Remove last element of the breadcrums to go up one level
            print("Button LEFT")
            self._submenu_index = 0
            
        elif button == ButtonCode.ESCAPE:
            print("Button ESCAPE")
            self._breadcrums.pop()
            
            new_active_menu_item = self._get_current_menu_item(self._breadcrums)
            new_active_menu_item.on_exit()

            
        return self._state


def test(menu, buttoncode):
    print(f"Menu: {menu.text()}")
    return menu.button_event(buttoncode, None)


if __name__ == "__main__":
    m = Menu()
    #m.show_menu_struct()
    m.add_menu_item(["musc", "volume"],
                    on_enter = None,
                    on_process = None,
                    on_exit = None)
    m.add_menu_item(["alm1", "time"],
                  on_enter = None,
                  on_process = None,
                  on_exit = None)
    m.add_menu_item(["alm1", "days"],
                  on_enter = None,
                  on_process = None,
                  on_exit = None)
    m.start()
    m.show_menu_struct()

    while m.text() != "exit":
        res = test(m, ButtonCode.DOWN)
        print(f"state = {res}")

    res = test(m, ButtonCode.RIGHT)
    print(f"state = {res}")
    
