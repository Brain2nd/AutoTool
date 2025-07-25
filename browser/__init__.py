"""
tool/browser 包

包含供浏览器自动化工具使用的辅助函数
"""

from .function.connect_to_chrome import *
from .function.create_new_tab import *
from .function.direct_click_in_iframe import *
from .function.extract_tag_from_selector import *
from .function.find_and_click_list_items import *
from .function.find_and_click_role_list_items import *
from .function.find_and_save_elements import *
from .function.find_elements_by_class import *
from .function.find_elements_by_similarity import *
from .function.find_elements_by_role import *
from .function.get_clickable_elements import *
from .function.get_page_dom import *
from .function.get_pages import *
from .function.list_saved_elements import *
from .function.load_elements import *
from .function.click_saved_element import *
from .function.navigate import *
from .function.navigate_page import *
from .function.navigate_to_url import *
from .function.simplify_selector import *
from .function.switch_page import *
from .function.wait_and_get_page_info import *
from .function.screenshot import *