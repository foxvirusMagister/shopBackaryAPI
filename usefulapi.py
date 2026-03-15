from typing import Optional
import operator

class UsefulAPI:
    @staticmethod
    def filter_items(selection, model, filter: str, possible_filters: List[str]):
        filter = filter.split(" ")
        if len(filter) == 3:
            if not filter[0] in possible_filters:
                raise Exception(f"Unknown filter in {possible_filters}, we want to find {filter[0]}")
            operation = getattr(operator, filter[1])
            if operation:
                parameter = getattr(model, filter[0])
                return selection.filter(operation(parameter, filter[2]))
            raise Exception(f"Wrong operation {filter[1]}")
        raise Exception(f"Wrong count of arguments: {len(filter)}, 3 expected")

    @staticmethod
    def sort_items(selection, model, sort: str, possible_sortings: List[str]):
        sign = "asc"
        if sort[0] == "-":
            sign = "desc"
            sort = sort[1:]
        elif sort[0] == "+":
            sort = sort[1:]
        if sort in possible_sortings:
            order = getattr(model, sort)
            order_direction = getattr(order, sign)
            return selection.order_by(order_direction())
        raise Exception(f"Incorrect sorting {sort}, expected {possible_sortings}")
    
    @staticmethod
    def paginate_items(selection, model, page: int, limit: Optional[int]):
        if limit != None:
            return selection.offset(limit * page).limit(limit)
        return selection
    
    @staticmethod
    def all_in_one(selection, model, filter: str, sort: str, fields: List[str], page: int, limit: Optional[int]):
        filtration = UsefulAPI.filter_items(selection, model, filter, fields)
        sorting = UsefulAPI.sort_items(filtration, model, sort, fields)
        pagination = UsefulAPI.paginate_items(sorting, model, page, limit)
        return pagination
    