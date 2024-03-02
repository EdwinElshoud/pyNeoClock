import helpers

ButtonCode = helpers.enum(ESCAPE=1, UP=2, DOWN=3, LEFT=4, RIGHT=5)
MenuState = helpers.enum(DISABLED=0, IN_MENU=1, IN_CALLBACK=2, EXIT=3)

class Menu:
    def __init__(self):
        self._structure = {}
        self._structure["exit"] = {"return_code": MenuState.EXIT,}   
        self._breadcrums = []
        self._menu_index = 0

    def __repr__(self):
        return str(self._structure)
    
    def reset(self):
        self._menu_index = 0
        self._breadcrums = []
        
    def add_item(self, path, callback, kwargs=None):
        print(path)
        parser = self._structure
        last_element = path.pop()
        print("last element: ", last_element)
        for i in path:
            print(f"Entering {i}")
            if i not in parser:
                # Creating path when path elements do not exist
                parser[i] = {"return_code": MenuState.IN_MENU}
            parser = parser[i]
        print("Adding to parser : ", last_element)    
        parser[last_element] = {"callback": callback, "kwargs": kwargs, "return_code": MenuState.IN_CALLBACK}

    def _jump_into_menu(self, breadcrum):
        """
        :param breadcrum: list of elements in the menu to traverse

        :return: sub dict of the menu
        """
        parser = self._structure
        for i in breadcrum:
            #print(f"Entering {i}")
            parser = parser[i]
        return parser
        
    def _menu_item(self, label):
        return {key: value for key, value in self._structure.items() if key == label}

    def _next_index(self, menu_list):
        if self._menu_index < len(menu_list)-1:
            self._menu_index = self._menu_index + 1 
        else:
            self._menu_index = 0
            
    def _prev_index(self, menu_list):
        if self._menu_index > 0: 
            self._menu_index = self._menu_index - 1 
        else:
            self._menu_index = len(menu_list) - 1
            
    def menu_text(self):
        """
        Get the name of the current menu item
        """
        active_menu = self._jump_into_menu(self._breadcrums)
        menu_keys = list(active_menu.keys())
        text = menu_keys[self._menu_index]
        if text == "return_code":
            return None
        
        return menu_keys[self._menu_index]
    
    def button_event(self, button, event):
        active_menu = self._jump_into_menu(self._breadcrums)
        menu_keys = list(active_menu.keys())
        #print(f"Breadcrums = {self._breadcrums}")
        #print(f"Menu = {menu_keys}")
        #print(f"Menu index = {self._menu_index}")

        # Forward to callback function
        has_callback = "callback" in menu_keys
        if has_callback and button is not ButtonCode.ESCAPE:
            print("Forwarding to callback function!!!")
            kwargs = active_menu["kwargs"]
            if kwargs is None:
                kwargs = {}
            kwargs["button"] = button
            kwargs["event"] = event
            active_menu["callback"](**kwargs)
            print("Return code (1) : ", active_menu["return_code"])
            return active_menu["return_code"]
            
        # Else handle menu control
        if button == ButtonCode.DOWN:
            print("Down button")
            self._next_index(menu_keys)
            #print(f"  --> {menu_keys[self._menu_index]}")
        elif button == ButtonCode.UP:
            print("Up button")
            self._prev_index(menu_keys)            
            #print(f"  --> {menu_keys[self._menu_index]}")
        elif button == ButtonCode.RIGHT:
            print("Right button")
            keyword_active_menu = menu_keys[self._menu_index]
            if "return_code" in menu_keys and active_menu["return_code"] == MenuState.EXIT:
                print("active_menu : ", active_menu)
                return MenuState.EXIT
            
            if "callback" in active_menu[keyword_active_menu]:
                print("Active menu: ", active_menu[keyword_active_menu])
                print("callback: ", active_menu[keyword_active_menu]["callback"])
                kwargs = active_menu[keyword_active_menu]["kwargs"]
                if kwargs is None:
                    kwargs = {}
                kwargs["button"] = None
                kwargs["event"] = event
                active_menu[keyword_active_menu]["callback"](**kwargs)
                
                self._breadcrums.append(keyword_active_menu)
                return MenuState.IN_CALLBACK
            else:
                self._breadcrums.append(menu_keys[self._menu_index])
                new_entry = self._jump_into_menu(self._breadcrums).keys()
                #if "callback" in new_entry:
                #    print(f"Should be execting the callback for {menu_keys[self._menu_index]}")
                #    #new_entry["callback"](**active_menu["kwargs"])
                #    return MenuState.IN_CALLBACK
                self._menu_index = 0
        elif button == ButtonCode.ESCAPE:
            print("Escape button")
            if len(self._breadcrums) > 0:
                # Remove last element from the breadcrums
                self._breadcrums = self._breadcrums[:-1]
                #print(f"  --> returning to {self._breadcrums}")
                self._menu_index = 0
                
        return MenuState.IN_MENU
