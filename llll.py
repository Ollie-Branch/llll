from enum import Enum, auto
from dataclasses import dataclass
import getopt, sys

class TokenType(Enum):
    PAREN_OPEN = auto()
    PAREN_CLOSE = auto()
    ATOM = auto()
    STR = auto()
    NUM = auto()
    ERR = auto()

@dataclass
class Token:
    type: TokenType
    value: str
    line: int

class Lexer:
    def __init__(self, text):
        self.text: str = text
        self.pos: int = 0
        self.line: int = 1
        self.tokens: Token = []

    def error(self, message):
        raise ValueError(f"Lexer error at line {self.line}: {message}")

    def discard_comment(self, i: int,
                        chars: list[str]) -> int:
        """ This function advances to the newline after spotting a comment
        symbol, semicolons denote comments in lisp. We return the current index
        we're reading after finding the newline """
        discarding_comment: bool = True
        while discarding_comment:
            char = chars[i]
            if char != "\n":
                i += 1
            else:
                discarding_comment = False
                return i

    def read_atom(self, i: int,
                  line_num: int,
                  atom_err_chars: str,
                  chars: list[str]) -> tuple[int, Token]:
        """ An atom starts with either an alphabetical character or a symbol
        (that isn't a parenthesis, bracket, or quote). We read the atom until we
        encounter a space, newline, quote, or parenthesis. If we encounter a
        quote or number, we should error and stop execution entirely. If we
        encounter a space, newline, or parenthesis, we stop reading the atom,
        return the current index and accumulated token. """
        reading_atom: bool = True
        atom_str: str = ""
        while reading_atom:
            char = chars[i]
            # check errors and token termination first so we don't accidentally
            # advance too far
            if char in atom_err_chars:
                # terminate reading and return error
                error_msg = "Atoms cannot contain quotes or numbers"
                reading_atom = False
                return (i, Token(TokenType.ERR, error_msg, self.line))
            elif char.isspace() or char in "()\n":
                # Terminate atom and return
                reading_atom = False
                return (i, Token(TokenType.ATOM, atom_str, self.line))
            else:
                # Accumulate atom
                atom_str = atom_str + char
                i += 1

    def read_str(self, i: int,
                 line_num: int,
                 str_termination_char: str,
                 chars: list[str]) -> tuple[int, Token]:
        """ A string starts with a double quote, we continue reading
        until we find a duplicate double quote. There should also be
        look-ahead to determine escape characters so we can include quotes
        inside our string. Once we find a final quote matching our original
        quote character, we will terminate reading, return the index after the
        final quote and return the accumulated token. """
        #TODO: implement escape character handling
        reading_str: bool = True
        str_str: str = ""
        # We immediately add the beginning quote and advance the index so we
        # don't infinitely call this function repeatedly cause we reference
        # the same quote character forever.
        str_str = str_str + chars[i]
        i += 1
        while reading_str:
            char = chars[i]
            if char in str_termination_char:
                # terminate the string and return the index and token, we
                # include the last quote so we don't return to the
                # main lexer loop and immediately restart this function
                # erroneously since the index would still be on a quote
                # character.
                str_str = str_str + char
                i += 1
                reading_string = False
                return (i, Token(TokenType.STR, str_str, self.line))
            elif char == "\n":
                self.line += 1
                str_str = str_str + char
                i += 1
            else:
                str_str = str_str + char
                i += 1
            
    def read_num(self, i: int,
                 line_num: int,
                 num_error_chars: str,
                 chars: list[str]) -> tuple[int, Token]:
        """ A number starts with a numeral character or period, and we continue
        reading until we find a space, symbol, or alphabet character. If we find
        a symbol or alphabet character, we error out, else we terminate reading
        the number, return the final index, and return the accumulated token.
        """
        reading_num: bool = True
        num_str: str = ""
        while reading_num:
            char = chars[i]
            if char in num_error_chars:
                # terminate and return error
                error_msg = "Numbers cannot contain anything other than numerals and periods"
                return (i, Token(TokenType.ERR, error_msg, self.line))
            elif char.isspace() or char in "()\n":
                reading_num = False
                return (i, Token(TokenType.NUM, num_str, self.line))
            else:
                # accumulate num and update index
                num_str = num_str + char
                i += 1

    def tokenize(self):
        chars = list(self.text)
        # The characters that can initialize an atom
        atom_start_chars: str = (
            'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
            "#+-*=/%<>!&|^~?")
        # The characters that can initialize a string
        str_start_chars: str = '"'
        # The characters that can initialize a number
        num_start_chars: str = '0123456789'
        i = 0
        while i < len(chars):
            char = chars[i]
            if char == "\n":
                self.line += 1
                i += 1
            elif char.isspace():
                # ignore and advance the index
                i += 1
            elif char == ";":
                i = self.discard_comment(i, chars)
            elif char == "(":
                self.tokens.append(Token(TokenType.PAREN_OPEN, '(', self.line))
                i += 1
            elif char == ")":
                self.tokens.append(Token(TokenType.PAREN_CLOSE, ')', self.line))
                i += 1
            # quoting support, separate the quote into its own atom
            elif char == "'":
                self.tokens.append(Token(TokenType.ATOM, "'", self.line))
                i += 1
            # atoms can start with periods too but I'd have to refactor to
            # properly add periods to atom start chars (because the number
            # reading code depends on using atom_start_chars for detecting
            # errors).
            elif char in atom_start_chars or char == ".":
                atom_token: Token
                i, atom_token = self.read_atom(i,
                                               self.line,
                                               str_start_chars + num_start_chars,
                                               chars)
                self.tokens.append(atom_token)
            elif char in str_start_chars:
                str_token: Token
                i, str_token = self.read_str(i,
                                        self.line,
                                        char,
                                        chars)
                self.tokens.append(str_token)
            elif char in num_start_chars:
                num_token: Token
                i, num_token = self.read_num(i,
                                        self.line,
                                        atom_start_chars + str_start_chars,
                                        chars)
                self.tokens.append(num_token)
        return self.tokens

if __name__ == "__main__":
    code: str = ""

    args = sys.argv[1:]
    options = "f:"
    long_options = ["file"]

    arguments, values = getopt.getopt(args, options, long_options)
    for currentArg, currentVal in arguments:
        if currentArg in ("-f", "--file"):
            with open(currentVal, "r") as file:
                code = file.read()
            lexer = Lexer(code)
            tokens = lexer.tokenize()
            for token in tokens:
                print(f"{token.type.name}: {token.value} (Line {token.line})")
        else:
            print ("Usage: llll.py -f $FILE")
