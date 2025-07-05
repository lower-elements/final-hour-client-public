def direction(num):
    '''return's a string representation of {direction}'''
    val=int((num/22.5)+.5)
    arr=["North","NorthNorthEast","NorthEast","EastNorthEast","East","EastSouthEast", "SouthEast", "SouthSouthEast","South","SouthSouthWest","SouthWest","WestSouthWest","West","WestNorthWest","NorthWest","NorthNorthWest"]
    return arr[(val % 16)]