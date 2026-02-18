#include <chrono>
#include <cstring>
#include <iostream>
#include <string>
#include <thread>

namespace {
bool has_flag(int argc, char* argv[], const char* flag) {
  for (int i = 1; i < argc; ++i) {
    if (std::strcmp(argv[i], flag) == 0) {
      return true;
    }
  }
  return false;
}
}  // namespace

int main(int argc, char* argv[]) {
  try {
    const bool smoke = has_flag(argc, argv, "--smoke");
    if (smoke) {
      std::cout << "[ctcp_headless] smoke start\n";
      std::this_thread::sleep_for(std::chrono::milliseconds(60));
      std::cout << "[ctcp_headless] smoke ok\n";
      return 0;
    }

    std::cout << "ctcp headless engine\n";
    std::cout << "Use --smoke for startup sanity check.\n";
    return 0;
  } catch (const std::exception& ex) {
    std::cerr << "[ctcp_headless][fatal] " << ex.what() << "\n";
    return 2;
  } catch (...) {
    std::cerr << "[ctcp_headless][fatal] unknown exception\n";
    return 3;
  }
}

