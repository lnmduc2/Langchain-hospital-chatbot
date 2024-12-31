import dotenv
dotenv.load_dotenv()


from wait_times import (
    get_current_wait_times,
    get_most_available_hospital,
)

print(get_current_wait_times("Wallace-Hamilton"))


print(get_current_wait_times("fake hospital"))


print(get_most_available_hospital(None))