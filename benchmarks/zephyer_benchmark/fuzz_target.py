from boofuzz import *


def main():
  session = Session(target=Target(
      connection=SocketConnection("host.docker.internal", 6666, proto='tcp')))
  s_initialize("request")
  s_string("FUZZ", fuzzable=True)
  session.connect(s_get("request"))
  session.fuzz()


if __name__ == "__main__":
  main()
