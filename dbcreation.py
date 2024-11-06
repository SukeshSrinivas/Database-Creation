from shiny import App, render, ui, reactive
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, ForeignKey
import plotly.graph_objects as go

# Database setup - Persistent SQLite file
engine = create_engine('sqlite:///digital_twin.db')  # Save data persistently
metadata = MetaData()

# Mapping for data types
DATA_TYPE_MAP = {
    "Integer": Integer,
    "Varchar": String
}

# Entity and Relationship classes
class Entity:
    def __init__(self, name, attributes, primary_key):
        self.name = name
        self.attributes = attributes
        self.primary_key = primary_key

class Relationship:
    def __init__(self, parent, child, type):
        self.parent = parent
        self.child = child
        self.type = type

# UI definition
app_ui = ui.page_fluid(
    ui.h1("Digital Twin Database Designer"),
    
    ui.navset_tab(
        ui.nav_panel("Define Entities",
            ui.h3("Entity Definition"),
            ui.input_text("entity_name", "Entity Name"),
            ui.input_text("attribute_name", "Attribute Name"),
            ui.input_select("data_type", "Data Type", choices=list(DATA_TYPE_MAP.keys())),
            ui.input_checkbox("is_primary_key", "Primary Key"),
            ui.input_action_button("add_entity", "Add Entity")
        ),
        ui.nav_panel("Define Relationships",
            ui.h3("Relationship Definition"),
            ui.output_ui("parent_entity_ui"),  # Output UI for dynamic dropdown
            ui.output_ui("child_entity_ui"),   # Output UI for dynamic dropdown
            ui.input_select("relationship_type", "Relationship Type", choices=["One-to-Many", "Many-to-Many"]),
            ui.input_action_button("add_relationship", "Add Relationship")
        ),
        ui.nav_panel("Schema Visualization",
            ui.h3("Schema Visualization"),
            ui.output_plot("schema_diagram")
        )
    )
)

# Server logic
def server(input, output, session):
    entities = reactive.Value([])       # Stores list of entities
    relationships = reactive.Value([])  # Stores list of relationships

    # Function to add a new entity
    @reactive.Effect
    @reactive.event(input.add_entity)
    def add_entity():
        entity_name = input.entity_name()
        attribute_name = input.attribute_name()
        data_type = DATA_TYPE_MAP[input.data_type()]  # Map the string to the SQLAlchemy type
        is_primary_key = input.is_primary_key()

        # Define a new entity and add it to entities list
        new_entity = Entity(entity_name, [(attribute_name, data_type)], is_primary_key)
        entities.set(entities.get() + [new_entity])

        # Create a table in the database using SQLAlchemy
        columns = [Column(attribute_name, data_type, primary_key=is_primary_key)]
        try:
            Table(entity_name, metadata, *columns, extend_existing=True)
            metadata.create_all(engine)  # Create tables in the database with engine
        except Exception as e:
            print(f"Error creating table {entity_name}: {e}")

    # Dynamic dropdown for parent entity
    @output
    @render.ui
    def parent_entity_ui():
        # Retrieve all entity names for dropdown choices
        return ui.input_select("parent_entity", "Parent Entity", choices=[e.name for e in entities.get()])

    # Dynamic dropdown for child entity
    @output
    @render.ui
    def child_entity_ui():
        # Retrieve all entity names for dropdown choices
        return ui.input_select("child_entity", "Child Entity", choices=[e.name for e in entities.get()])

    # Function to add a new relationship
    @reactive.Effect
    @reactive.event(input.add_relationship)
    def add_relationship():
        parent = input.parent_entity()
        child = input.child_entity()
        relationship_type = input.relationship_type()

        # Define a new relationship and add to relationships list
        new_relationship = Relationship(parent, child, relationship_type)
        relationships.set(relationships.get() + [new_relationship])

        # Add foreign key relationships in the schema if necessary
        if relationship_type == "One-to-Many":
            parent_table = metadata.tables.get(parent)
            child_table = metadata.tables.get(child)
            if parent_table and child_table:
                try:
                    fk_column = Column(f"{parent}_id", Integer, ForeignKey(f"{parent}.id"))
                    child_table.append_column(fk_column)
                    metadata.create_all(engine)
                except Exception as e:
                    print(f"Error creating relationship {parent} -> {child}: {e}")

    # Function to display schema diagram
    @output
    @render.plot
    def schema_diagram():
        fig = go.Figure()

        # Add nodes for each entity
        x_pos, y_pos = 0, 0
        for i, entity in enumerate(entities.get()):
            x_pos, y_pos = i * 1.5, 0
            fig.add_trace(go.Scatter(x=[x_pos], y=[y_pos], mode='markers+text', text=entity.name, textposition="top center"))

        # Add edges for each relationship
        for relationship in relationships.get():
            fig.add_trace(go.Scatter(x=[0, 1.5], y=[0, 0], mode='lines+text', text=f"{relationship.parent} -> {relationship.child}", textposition="middle right"))

        fig.update_layout(title="Schema Diagram", showlegend=False)


app = App(app_ui, server)
