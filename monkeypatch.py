#this is required to get around the new Chrome restriction on cross-domain cookies - see https://blog.chromium.org/2019/10/developers-get-ready-for-new.html
from http.cookies import Morsel
Morsel._reserved["samesite"] = "SameSite"