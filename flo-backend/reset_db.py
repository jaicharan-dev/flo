from models import Base, engine

print("Dropping all local tables...")
Base.metadata.drop_all(bind=engine)

print("Rebuilding tables with new safe cascade rules...")
Base.metadata.create_all(bind=engine)

print("Local Database successfully reset!")