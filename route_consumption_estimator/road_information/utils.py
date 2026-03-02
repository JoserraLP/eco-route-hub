def split_list(list_data: list, n: int):
    """
    Split a list into list of n size

    :param list_data: list with the data
    :type list_data: list
    :param n: number of items per sublist
    :type n: int
    :return:
    """
    # Iterate over the list and retrieve the requested sublist
    for i in range(0, len(list_data), n):
        yield list_data[i:i + n]



