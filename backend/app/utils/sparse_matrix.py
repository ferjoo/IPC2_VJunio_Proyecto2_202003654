class SparseMatrix:
    """
    Implementación de Matriz Dispersa usando diccionarios para almacenar elementos no-cero.
    Eficiente para matrices con muchos elementos cero.
    """
    
    def __init__(self, rows, cols):
        """
        Inicializa una matriz dispersa con las dimensiones dadas.
        
        Args:
            rows (int): Número de filas
            cols (int): Número de columnas
        """
        self.rows = rows
        self.cols = cols
        self.data = {}  # Diccionario para almacenar elementos no-cero: (fila, col) -> valor
    
    def set_value(self, row, col, value):
        """
        Establece un valor en la posición especificada.
        
        Args:
            row (int): Índice de fila (base 0)
            col (int): Índice de columna (base 0)
            value (float/int): Valor a establecer
        """
        if 0 <= row < self.rows and 0 <= col < self.cols:
            if value != 0:
                self.data[(row, col)] = value
            elif (row, col) in self.data:
                del self.data[(row, col)]
    
    def get_value(self, row, col):
        """
        Obtiene el valor en la posición especificada.
        
        Args:
            row (int): Índice de fila (base 0)
            col (int): Índice de columna (base 0)
            
        Returns:
            float/int: Valor en la posición (fila, col), 0 si no se encuentra
        """
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return self.data.get((row, col), 0)
        return 0
    
    def get_non_zero_elements(self):
        """
        Obtiene todos los elementos no-cero como un diccionario.
        
        Returns:
            dict: Diccionario con claves (fila, col) y sus valores
        """
        return self.data.copy()
    
    def get_row(self, row):
        """
        Obtiene todos los elementos en una fila específica.
        
        Args:
            row (int): Índice de fila (base 0)
            
        Returns:
            dict: Diccionario con índices de columna como claves y valores
        """
        if 0 <= row < self.rows:
            row_data = {}
            for (r, c), value in self.data.items():
                if r == row:
                    row_data[c] = value
            return row_data
        return {}
    
    def get_column(self, col):
        """
        Obtiene todos los elementos en una columna específica.
        
        Args:
            col (int): Índice de columna (base 0)
            
        Returns:
            dict: Diccionario con índices de fila como claves y valores
        """
        if 0 <= col < self.cols:
            col_data = {}
            for (r, c), value in self.data.items():
                if c == col:
                    col_data[r] = value
            return col_data
        return {}
    
    def add(self, other):
        """
        Suma otra matriz dispersa a esta.
        
        Args:
            other (SparseMatrix): Matriz a sumar
            
        Returns:
            SparseMatrix: Nueva matriz con el resultado
        """
        if self.rows != other.rows or self.cols != other.cols:
            raise ValueError("Las dimensiones de las matrices deben coincidir para la suma")
        
        result = SparseMatrix(self.rows, self.cols)
        
        # Copia todos los elementos de esta matriz
        for (r, c), value in self.data.items():
            result.set_value(r, c, value)
        
        # Suma elementos de la otra matriz
        for (r, c), value in other.data.items():
            current_value = result.get_value(r, c)
            result.set_value(r, c, current_value + value)
        
        return result
    
    def multiply(self, other):
        """
        Multiplica esta matriz por otra matriz dispersa.
        
        Args:
            other (SparseMatrix): Matriz por la cual multiplicar
            
        Returns:
            SparseMatrix: Nueva matriz con el resultado
        """
        if self.cols != other.rows:
            raise ValueError("Las dimensiones de las matrices son incompatibles para la multiplicación")
        
        result = SparseMatrix(self.rows, other.cols)
        
        # Para cada elemento no-cero en esta matriz
        for (r1, c1), value1 in self.data.items():
            # Para cada elemento no-cero en la fila correspondiente de la otra matriz
            for (r2, c2), value2 in other.data.items():
                if c1 == r2:  # La columna de la primera matriz coincide con la fila de la segunda matriz
                    current_value = result.get_value(r1, c2)
                    result.set_value(r1, c2, current_value + value1 * value2)
        
        return result
    
    def transpose(self):
        """
        Transpone la matriz.
        
        Returns:
            SparseMatrix: Matriz transpuesta
        """
        result = SparseMatrix(self.cols, self.rows)
        
        for (r, c), value in self.data.items():
            result.set_value(c, r, value)
        
        return result
    
    def get_density(self):
        """
        Calcula la densidad de la matriz (porcentaje de elementos no-cero).
        
        Returns:
            float: Densidad como porcentaje
        """
        total_elements = self.rows * self.cols
        non_zero_count = len(self.data)
        return (non_zero_count / total_elements) * 100 if total_elements > 0 else 0
    
    def to_string(self):
        """
        Convierte la matriz a representación de cadena.
        
        Returns:
            str: Representación de cadena de la matriz
        """
        lines = []
        for row in range(self.rows):
            row_str = []
            for col in range(self.cols):
                value = self.get_value(row, col)
                row_str.append(str(value))
            lines.append(" ".join(row_str))
        return "\n".join(lines)
    
    def __str__(self):
        return self.to_string()
    
    def __repr__(self):
        return f"SparseMatrix({self.rows}x{self.cols}, {len(self.data)} elementos no-cero)"


def create_sparse_matrix_from_data(rows, cols, data_dict):
    """
    Crea una matriz dispersa desde un diccionario de datos.
    Args:
        rows (int): Número de filas
        cols (int): Número de columnas
        data_dict (dict): Diccionario con claves (fila, col) o 'fila,col' y valores
    Returns:
        SparseMatrix: Nueva matriz dispersa
    """
    matrix = SparseMatrix(rows, cols)
    for key, value in data_dict.items():
        if isinstance(key, str):
            row, col = map(int, key.split(','))
        else:
            row, col = key
        matrix.set_value(row, col, value)
    return matrix


def create_identity_matrix(size):
    """
    Crea una matriz identidad del tamaño dado.
    
    Args:
        size (int): Tamaño de la matriz identidad
        
    Returns:
        SparseMatrix: Matriz identidad
    """
    matrix = SparseMatrix(size, size)
    for i in range(size):
        matrix.set_value(i, i, 1)
    return matrix


def create_zero_matrix(rows, cols):
    """
    Crea una matriz cero con las dimensiones dadas.
    
    Args:
        rows (int): Número de filas
        cols (int): Número de columnas
        
    Returns:
        SparseMatrix: Matriz cero
    """
    return SparseMatrix(rows, cols) 