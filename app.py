from typing import Dict, Any, List
import streamlit as st
import os
from datetime import datetime, timedelta, date
import json
import asyncio
from src.script_ingestion.coordinator import ScriptIngestionCoordinator
from src.one_liner.coordinator import OneLinerCoordinator
from src.character_breakdown.coordinator import CharacterBreakdownCoordinator
from src.scheduling.coordinator import SchedulingCoordinator
from src.budgeting.coordinator import BudgetingCoordinator
from src.storyboard.coordinator import StoryboardCoordinator
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize coordinators
script_coordinator = ScriptIngestionCoordinator()
one_liner_coordinator = OneLinerCoordinator()
character_coordinator = CharacterBreakdownCoordinator()
scheduling_coordinator = SchedulingCoordinator()
budgeting_coordinator = BudgetingCoordinator()
storyboard_coordinator = StoryboardCoordinator()

# Knowledge base storage
STORAGE_DIR = "static/storage"
os.makedirs(STORAGE_DIR, exist_ok=True)

def save_to_storage(data: dict, filename: str):
    """Save data to storage with timestamp."""
    filepath = os.path.join(STORAGE_DIR, filename)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    return filepath

def load_from_storage(filename: str) -> dict:
    """Load data from storage."""
    filepath = os.path.join(STORAGE_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return json.load(f)
    return {}

def main():
    st.title("Film Production Assistant")
    
    # Initialize session state
    if 'current_step' not in st.session_state:
        st.session_state.current_step = 'upload'
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    steps = ['Upload Script', 'Script Analysis', 'One-Liner', 'Character Breakdown', 'Schedule', 'Budget', 'Storyboard', 'Overview']
    current_step = st.sidebar.radio("Go to", steps)
    
    if current_step == 'Upload Script':
        show_upload_page()
    elif current_step == 'Script Analysis':
        show_script_analysis()
    elif current_step == 'One-Liner':
        show_one_liner()
    elif current_step == 'Character Breakdown':
        show_character_breakdown()
    elif current_step == 'Schedule':
        show_schedule()
    elif current_step == 'Budget':
        show_budget()
    elif current_step == 'Storyboard':
        show_storyboard()
    elif current_step == 'Overview':
        show_overview()

def show_upload_page():
    st.header("Upload Script")
    
    # Add tabs for different input methods
    tab1, tab2 = st.tabs(["Upload File", "Paste Text"])
    
    with tab1:
        uploaded_file = st.file_uploader("Choose a script file", type=['txt'])
        
        if uploaded_file is not None:
            st.success(f"File uploaded: {uploaded_file.name}")
            col1, col2 = st.columns([1, 2])
            with col1:
                submit_button = st.button("Submit and Process", key="submit_file", type="primary")
            
            if submit_button:
                script_path = os.path.join(STORAGE_DIR, 'uploaded_script.txt')
                with open(script_path, 'wb') as f:
                    f.write(uploaded_file.getvalue())
                
                with st.spinner("Processing script through ingestion pipeline..."):
                    try:
                        # Read the script content
                        with open(script_path, 'r') as f:
                            script_content = f.read()
                        
                        # Process through script ingestion pipeline
                        script_data = asyncio.run(script_coordinator.process_script(script_content))
                        
                        if "error" in script_data:
                            st.error(f"Script processing failed: {script_data['error']}")
                            # Show detailed error information if available
                            with st.expander("View Error Details"):
                                if "details" in script_data:
                                    st.text("Error Details:")
                                    st.code(script_data["details"])
                                if "raw_response" in script_data:
                                    st.text("Raw Response:")
                                    st.code(script_data["raw_response"])
                                if "processing_log" in script_data:
                                    st.text("Processing Log:")
                                    st.json(script_data["processing_log"])
                        else:
                            save_to_storage(script_data, 'script_ingestion_results.json')
                            st.session_state.current_step = 'Script Analysis'
                            st.success("Script processed successfully! Redirecting to analysis...")
                            st.rerun()
                            
                    except Exception as e:
                        logger.error(f"Error processing script: {str(e)}", exc_info=True)
                        st.error(f"An unexpected error occurred: {str(e)}")
    
    with tab2:
        pasted_text = st.text_area("Paste your script here", height=400, placeholder="Enter your script text here...")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            submit_text_button = st.button("Submit and Process", key="submit_text", type="primary", disabled=not bool(pasted_text))
        
        if submit_text_button and pasted_text:
            with st.spinner("Processing script through ingestion pipeline..."):
                try:
                    # Process through script ingestion pipeline
                    script_data = asyncio.run(script_coordinator.process_script(pasted_text))
                    
                    if "error" in script_data:
                        st.error(f"Script processing failed: {script_data['error']}")
                        # Show detailed error information if available
                        with st.expander("View Error Details"):
                            if "details" in script_data:
                                st.text("Error Details:")
                                st.code(script_data["details"])
                            if "raw_response" in script_data:
                                st.text("Raw Response:")
                                st.code(script_data["raw_response"])
                            if "processing_log" in script_data:
                                st.text("Processing Log:")
                                st.json(script_data["processing_log"])
                    else:
                        save_to_storage(script_data, 'script_ingestion_results.json')
                        st.session_state.current_step = 'Script Analysis'
                        st.success("Script processed successfully! Redirecting to analysis...")
                        st.rerun()
                        
                except Exception as e:
                    logger.error(f"Error processing script: {str(e)}", exc_info=True)
                    st.error(f"An unexpected error occurred: {str(e)}")

def show_script_analysis():
    st.header("Script Analysis")
    results = load_from_storage('script_ingestion_results.json')
    
    if results:
        # Display parsed data
        st.subheader("Parsed Script Structure")
        if "parsed_data" in results:
            with st.expander("View Parsed Data", expanded=True):
                st.json(results["parsed_data"])
        
        # Display metadata
        st.subheader("Script Metadata")
        if "metadata" in results:
            with st.expander("View Metadata", expanded=True):
                st.json(results["metadata"])
        
        # Display validation results
        st.subheader("Validation Results")
        if "validation" in results:
            validation = results["validation"]
            if validation["is_valid"]:
                st.success("✅ Script validation passed")
            else:
                st.warning("⚠️ Script validation has issues")
            
            with st.expander("View Validation Details"):
                st.json(validation)
        
        # Navigation buttons
        col1, col2 = st.columns([1, 2])
        with col1:
            if st.button("Generate One-Liner", type="primary"):
                with st.spinner("Generating one-liner..."):
                    try:
                        one_liner_data = asyncio.run(one_liner_coordinator.generate_one_liner(results))
                        save_to_storage(one_liner_data, 'one_liner_results.json')
                        st.session_state.current_step = 'One-Liner'
                        st.success("One-liner generated successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error generating one-liner: {str(e)}")
            else:
                    st.warning("Please upload and process a script first.")
                    if st.button("Go to Upload", type="primary"):
                        st.session_state.current_step = 'Upload Script'
                        st.rerun()

def show_one_liner():
    st.header("One-Liner Summary")
    results = load_from_storage('one_liner_results.json')
    if results:
        st.json(results)
        if st.button("Analyze Characters"):
            with st.spinner("Analyzing characters..."):
                try:
                    script_data = load_from_storage('script_ingestion_results.json')
                    character_data = asyncio.run(character_coordinator.process_script(script_data))
                    save_to_storage(character_data, 'character_breakdown_results.json')
                    st.session_state.current_step = 'Character Breakdown'
                    st.success("Character analysis completed!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error analyzing characters: {str(e)}")
    else:
        st.warning("Please complete script analysis first.")

def show_character_breakdown():
    st.header("Character Breakdown")
    script_results = load_from_storage('script_ingestion_results.json')
    
    if not script_results:
        st.warning("Please upload and process a script first.")
        return
    
    # Add tabs for different views
    tab1, tab2, tab3 = st.tabs(["Visual Display", "JSON Format", "Raw Data"])
    
    with tab1:
        # Load character breakdown results
        breakdown_results = load_from_storage('character_breakdown_results.json')
        
        if not breakdown_results:
            if st.button("Generate Character Breakdown", type="primary"):
                with st.spinner("Analyzing characters..."):
                    try:
                        breakdown_results = asyncio.run(character_coordinator.generate_breakdown(script_results))
                        save_to_storage(breakdown_results, 'character_breakdown_results.json')
                        st.success("Character breakdown generated!")
                        st.rerun()
                    except Exception as e:
                        logger.error(f"Error generating character breakdown: {str(e)}", exc_info=True)
                        st.error(f"An error occurred: {str(e)}")
        else:
            # Display character information in a structured format
            if "characters" in breakdown_results:
                for char in breakdown_results["characters"]:
                    # Handle both string and dictionary character data
                    if isinstance(char, dict):
                        # For dictionary data, display detailed information
                        with st.expander(f"📋 {char.get('name', 'Unknown Character')}"):
                            col1, col2 = st.columns([1, 1])
                            with col1:
                                st.write("**Role Type:**", char.get("role_type", "N/A"))
                                st.write("**Scene Count:**", len(char.get("scenes", [])))
                            with col2:
                                st.write("**First Appearance:**", char.get("first_appearance", "N/A"))
                                st.write("**Last Appearance:**", char.get("last_appearance", "N/A"))
                            
                            if "description" in char:
                                st.write("**Description:**", char["description"])
                            
                            if "scenes" in char:
                                st.write("**Scenes:**")
                                for scene in char["scenes"]:
                                    st.write(f"- Scene {scene}")
                    else:
                        # For string data, display simple expander with character name
                        with st.expander(f"📋 {char}"):
                            st.write("Basic character information available")
                            st.write(f"Character Name: {char}")
                
                # Add button to generate schedule
                st.divider()
                col1, col2 = st.columns([1, 2])
                with col1:
                    if st.button("Generate Production Schedule", type="primary"):
                        st.session_state.current_step = 'Schedule'
                        st.rerun()
    
    with tab2:
        # Display formatted JSON
        if breakdown_results:
            st.json(breakdown_results)
            # Add button to generate schedule
            st.divider()
            col1, col2 = st.columns([1, 2])
            with col1:
                if st.button("Generate Production Schedule ", type="primary"):
                    st.session_state.current_step = 'Schedule'
                    st.rerun()
        else:
            st.info("No character breakdown data available. Generate a breakdown first.")
    
    with tab3:
        # Display raw data in text format
        if breakdown_results:
            st.text_area("Raw JSON Data", value=json.dumps(breakdown_results, indent=2), height=400)
            # Add button to generate schedule
            st.divider()
            col1, col2 = st.columns([1, 2])
            with col1:
                if st.button("Generate Production Schedule  ", type="primary"):
                    st.session_state.current_step = 'Schedule'
                    st.rerun()
        else:
            st.info("No character breakdown data available. Generate a breakdown first.")

def show_schedule():
    st.header("Production Schedule")
    script_results = load_from_storage('script_ingestion_results.json')
    character_results = load_from_storage('character_breakdown_results.json')
    
    if not script_results or not character_results:
        st.warning("Please complete script analysis and character breakdown first.")
        return
    
    # Add tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["Schedule View", "JSON Format", "Raw Data", "Settings"])
    
    with tab1:
        # Load schedule results
        schedule_results = load_from_storage('schedule_results.json')
        
        if not schedule_results:
            col1, col2 = st.columns([2, 1])
            with col1:
                start_date = st.date_input("Schedule Start Date", min_value=date.today())
            
            if st.button("Generate Schedule", type="primary"):
                with st.spinner("Generating production schedule..."):
                    try:
                        schedule_results = asyncio.run(scheduling_coordinator.generate_schedule(
                            script_results,
                            character_results,
                            start_date.strftime("%Y-%m-%d")
                        ))
                        save_to_storage(schedule_results, 'schedule_results.json')
                        st.success("Schedule generated!")
                        st.rerun()
                    except Exception as e:
                        logger.error(f"Error generating schedule: {str(e)}", exc_info=True)
                        st.error(f"An error occurred: {str(e)}")
        else:
            # Display schedule in a structured format
            if "schedule" in schedule_results:
                for day in schedule_results["schedule"]:
                    if isinstance(day, dict):
                        # For dictionary data, display detailed schedule information
                        with st.expander(f"📅 Day {day.get('day_number', '?')} - {day.get('date', 'Unknown Date')}"):
                            st.write(f"**Day Start:** {day.get('day_start', 'N/A')}")
                            st.write(f"**Day Wrap:** {day.get('day_wrap', 'N/A')}")
                            
                            # Display scenes for the day
                            st.write("**Scenes:**")
                            scenes = day.get("scenes", [])
                            if isinstance(scenes, list):
                                for scene in scenes:
                                    if isinstance(scene, dict):
                                        st.write(f"- Scene {scene.get('scene_id', '?')}:")
                                        st.write(f"  Location: {scene.get('location', 'N/A')}")
                                        st.write(f"  Time: {scene.get('start_time', 'N/A')} - {scene.get('end_time', 'N/A')}")
                                    else:
                                        st.write(f"- Scene: {scene}")
                    else:
                        # For string data, display basic schedule information
                        with st.expander(f"📅 Schedule Entry"):
                            st.write(f"Basic schedule information: {day}")
                
                # Display efficiency metrics if available
                if isinstance(schedule_results.get("efficiency_metrics"), dict):
                    st.subheader("Efficiency Metrics")
                    metrics = schedule_results["efficiency_metrics"]
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Moves/Day", f"{metrics.get('company_moves_per_day', 'N/A')}")
                    with col2:
                        st.metric("Pages/Day", f"{metrics.get('average_pages_per_day', 'N/A')}")
                    with col3:
                        st.metric("Optimization Score", f"{metrics.get('location_optimization_score', 'N/A')}")
                
                # Add button to generate budget
                st.divider()
                col1, col2 = st.columns([1, 2])
                with col1:
                    if st.button("Generate Production Budget", type="primary"):
                        st.session_state.current_step = 'Budget'
                        st.rerun()
    
    with tab2:
        # Display formatted JSON
        if schedule_results:
            st.json(schedule_results)
            # Add button to generate budget
            st.divider()
            col1, col2 = st.columns([1, 2])
            with col1:
                if st.button("Generate Production Budget ", type="primary"):
                    st.session_state.current_step = 'Budget'
                    st.rerun()
        else:
            st.info("No schedule data available. Generate a schedule first.")
    
    with tab3:
        # Display raw data in text format
        if schedule_results:
            st.text_area("Raw JSON Data", value=json.dumps(schedule_results, indent=2), height=400)
            # Add button to generate budget
            st.divider()
            col1, col2 = st.columns([1, 2])
            with col1:
                if st.button("Generate Production Budget  ", type="primary"):
                    st.session_state.current_step = 'Budget'
                    st.rerun()
        else:
            st.info("No schedule data available. Generate a schedule first.")
    
    with tab4:
        st.subheader("Schedule Settings")
        st.write("Adjust these settings before generating a new schedule:")
        
        # Schedule constraints
        with st.expander("Time Constraints", expanded=True):
            max_hours = st.number_input("Maximum Hours per Day", min_value=8, max_value=14, value=12)
            meal_break = st.number_input("Meal Break Duration (minutes)", min_value=30, max_value=90, value=60)
            turnaround = st.number_input("Minimum Turnaround Time (hours)", min_value=8, max_value=12, value=10)
        
        # Location preferences
        with st.expander("Location Preferences"):
            max_moves = st.number_input("Maximum Company Moves per Day", min_value=1, max_value=5, value=2)
            prefer_grouping = st.checkbox("Prefer Location Grouping", value=True)
        
        # Save settings button
        if st.button("Save Settings"):
            settings = {
                "time_constraints": {
                    "max_hours_per_day": max_hours,
                    "meal_break_duration": meal_break,
                    "min_turnaround": turnaround
                },
                "location_preferences": {
                    "max_company_moves": max_moves,
                    "prefer_grouping": prefer_grouping
                }
            }
            save_to_storage(settings, 'schedule_settings.json')
            st.success("Settings saved! They will be applied to the next schedule generation.")

def show_budget():
    st.header("Production Budget")
    
    # Load required data from previous steps
    script_results = load_from_storage('script_ingestion_results.json')
    character_results = load_from_storage('character_breakdown_results.json')
    schedule_results = load_from_storage('schedule_results.json')
    
    if not script_results or not character_results or not schedule_results:
        st.warning("Please complete script analysis, character breakdown, and schedule generation first.")
        return
    
    # Add tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["Budget Overview", "JSON Format", "Raw Data", "Settings"])
    
    with tab1:
        # Load budget results
        budget_results = load_from_storage('budget_results.json')
        
        if not budget_results:
            col1, col2 = st.columns([2, 1])
            with col1:
                target_budget = st.number_input("Target Budget (Optional)", min_value=0.0, step=1000.0)
            
            # Production constraints input
            with st.expander("Production Constraints", expanded=True):
                quality_level = st.selectbox("Production Quality Level", ["High", "Medium", "Low"], index=1)
                equipment_preference = st.selectbox("Equipment Preference", ["Premium", "Standard", "Budget"], index=1)
                crew_size = st.selectbox("Crew Size", ["Large", "Medium", "Small"], index=1)
                
                constraints = {
                    "quality_level": quality_level,
                    "equipment_preference": equipment_preference,
                    "crew_size": crew_size,
                    "schedule_days": len(schedule_results.get("schedule", [])),
                    "total_scenes": len(script_results.get("parsed_data", {}).get("scenes", [])),
                    "total_characters": len(character_results.get("characters", []))
                }
            
            if st.button("Generate Budget", type="primary"):
                with st.spinner("Generating production budget..."):
                    try:
                        # Prepare production data
                        production_data = {
                            "script_metadata": script_results.get("metadata", {}),
                            "scene_count": constraints["total_scenes"],
                            "character_count": constraints["total_characters"],
                            "schedule_days": constraints["schedule_days"],
                            "quality_level": quality_level
                        }
                        
                        # Prepare location data from schedule
                        location_data = {
                            "locations": [
                                scene.get("location", "Unknown")
                                for day in schedule_results.get("schedule", [])
                                if isinstance(day, dict)
                                for scene in day.get("scenes", [])
                                if isinstance(scene, dict)
                            ]
                        }
                        
                        # Prepare crew data
                        crew_data = {
                            "size": crew_size,
                            "equipment_level": equipment_preference,
                            "departments": ["Production", "Camera", "Lighting", "Sound", "Art", "Makeup", "Wardrobe"]
                        }
                        
                        # Generate budget using coordinator
                        budget_results = asyncio.run(budgeting_coordinator.initialize_budget(
                            production_data=production_data,
                            location_data=location_data,
                            crew_data=crew_data,
                            target_budget=target_budget if target_budget > 0 else None,
                            constraints=constraints
                        ))
                        
                        save_to_storage(budget_results, 'budget_results.json')
                        st.success("Budget generated!")
                        st.rerun()
                    except Exception as e:
                        logger.error(f"Error generating budget: {str(e)}", exc_info=True)
                        st.error(f"An error occurred: {str(e)}")
        else:
            # Display budget overview in a structured format
            if "total_estimates" in budget_results:
                st.subheader("Budget Summary")
                total = budget_results["total_estimates"]
                
                # Display grand total
                st.metric("Total Budget", f"${total.get('grand_total', 0):,.2f}")
                
                # Display category breakdowns
                st.subheader("Cost Categories")
                cols = st.columns(3)
                categories = [
                    ("Location Costs", "total_location_costs"),
                    ("Equipment Costs", "total_equipment_costs"),
                    ("Personnel Costs", "total_personnel_costs"),
                    ("Logistics Costs", "total_logistics_costs"),
                    ("Insurance Costs", "total_insurance_costs"),
                    ("Contingency", "contingency_amount")
                ]
                
                for i, (label, key) in enumerate(categories):
                    with cols[i % 3]:
                        st.metric(label, f"${total.get(key, 0):,.2f}")
                
                # Display detailed breakdowns in expanders
                if "location_costs" in budget_results:
                    with st.expander("📍 Location Costs Breakdown"):
                        for loc, data in budget_results["location_costs"].items():
                            st.write(f"**{loc}**")
                            st.write(f"Daily Rate: ${data.get('daily_rate', 0):,.2f}")
                            st.write(f"Total Days: {data.get('total_days', 0)}")
                            st.write(f"Total Cost: ${data.get('total_cost', 0):,.2f}")
                
                if "equipment_costs" in budget_results:
                    with st.expander("🎥 Equipment Costs Breakdown"):
                        for category, data in budget_results["equipment_costs"].items():
                            st.write(f"**{category}**")
                            st.write(f"Total Cost: ${data.get('total_cost', 0):,.2f}")
                
                if "personnel_costs" in budget_results:
                    with st.expander("👥 Personnel Costs Breakdown"):
                        for role, data in budget_results["personnel_costs"].items():
                            st.write(f"**{role}**")
                            st.write(f"Daily Rate: ${data.get('daily_rate', 0):,.2f}")
                            st.write(f"Total Days: {data.get('total_days', 0)}")
                            st.write(f"Total Cost: ${data.get('total_cost', 0):,.2f}")
    
    with tab2:
        # Display formatted JSON
        if budget_results:
            st.json(budget_results)
        else:
            st.info("No budget data available. Generate a budget first.")
    
    with tab3:
        # Display raw data in text format
        if budget_results:
            st.text_area("Raw JSON Data", value=json.dumps(budget_results, indent=2), height=400)
        else:
            st.info("No budget data available. Generate a budget first.")
    
    with tab4:
        st.subheader("Budget Settings")
        st.write("Adjust these settings before generating a new budget:")
        
        # Budget constraints
        with st.expander("Budget Constraints", expanded=True):
            max_total = st.number_input("Maximum Total Budget", min_value=0.0, step=5000.0)
            contingency = st.slider("Contingency Percentage", min_value=5, max_value=20, value=10)
        
        # Department allocations
        with st.expander("Department Allocations"):
            st.write("Set maximum percentage allocations for each department:")
            production = st.slider("Production Department", 0, 100, 30)
            camera = st.slider("Camera Department", 0, 100, 20)
            lighting = st.slider("Lighting Department", 0, 100, 15)
            sound = st.slider("Sound Department", 0, 100, 10)
        
        # Save settings button
        if st.button("Save Settings"):
            settings = {
                "budget_constraints": {
                    "max_total": max_total,
                    "contingency_percentage": contingency
                },
                "department_allocations": {
                    "production": production / 100,
                    "camera": camera / 100,
                    "lighting": lighting / 100,
                    "sound": sound / 100
                }
            }
            save_to_storage(settings, 'budget_settings.json')
            st.success("Settings saved! They will be applied to the next budget generation.")

def show_storyboard():
    st.header("Storyboard Generation")
    
    # Load required data from previous steps
    script_results = load_from_storage('script_ingestion_results.json')
    
    if not script_results:
        st.warning("Please complete script analysis first.")
        return
    
    # Add a prominent storyboard generation button at the top
    st.subheader("Generate New Storyboard")
    if st.button("🎬 GENERATE STORYBOARD 🎬", key="main_storyboard_button", type="primary", use_container_width=True):
        with st.spinner("Generating storyboard images..."):
            try:
                # Generate storyboard using coordinator
                storyboard_results = asyncio.run(storyboard_coordinator.generate_storyboard(script_results))
                
                save_to_storage(storyboard_results, 'storyboard_results.json')
                st.success("Storyboard generated!")
                st.rerun()
            except Exception as e:
                logger.error(f"Error generating storyboard: {str(e)}", exc_info=True)
                st.error(f"An error occurred: {str(e)}")
    
    # Add tabs for different views
    tab1, tab2, tab3 = st.tabs(["Storyboard View", "JSON Format", "Settings"])
    
    with tab1:
        # Load storyboard results
        storyboard_results = load_from_storage('storyboard_results.json')
        
        if not storyboard_results:
            col1, col2 = st.columns([2, 1])
            
            # Storyboard generation options
            with st.expander("Storyboard Options", expanded=True):
                scenes_per_page = st.slider("Scenes Per Page", min_value=1, max_value=6, value=3)
                style_choice = st.selectbox("Visual Style", ["Realistic", "Cinematic", "Sketch", "Comic"], index=1)
                include_text = st.checkbox("Include Scene Text", value=True)
                
                settings = {
                    "scenes_per_page": scenes_per_page,
                    "style": style_choice,
                    "include_text": include_text
                }
            
            # Secondary button at the bottom of the options
            if st.button("Generate Storyboard", key="secondary_storyboard_button", type="primary"):
                with st.spinner("Generating storyboard images..."):
                    try:
                        # Generate storyboard using coordinator
                        storyboard_results = asyncio.run(storyboard_coordinator.generate_storyboard(script_results))
                        
                        save_to_storage(storyboard_results, 'storyboard_results.json')
                        st.success("Storyboard generated!")
                        st.rerun()
                    except Exception as e:
                        logger.error(f"Error generating storyboard: {str(e)}", exc_info=True)
                        st.error(f"An error occurred: {str(e)}")
        else:
            # Display storyboard images
            if "scenes" in storyboard_results:
                st.subheader("Storyboard Images")
                
                # Organize scenes into rows
                scenes = storyboard_results.get("scenes", [])
                rows = []
                num_cols = 3  # Number of images per row
                
                for i in range(0, len(scenes), num_cols):
                    rows.append(scenes[i:i+num_cols])
                
                # Display images in a grid layout
                for row in rows:
                    cols = st.columns(num_cols)
                    for i, scene in enumerate(row):
                        if i < len(cols):
                            with cols[i]:
                                if "image_path" in scene and scene["image_path"]:
                                    # Display the image
                                    st.image(scene["image_path"], caption=f"Scene {scene.get('scene_id', '?')}")
                                    
                                    # Display scene info in expander
                                    with st.expander("Scene Details"):
                                        st.write(f"**Scene:** {scene.get('scene_id', 'Unknown')}")
                                        st.write(f"**Description:** {scene.get('scene_heading', 'No description')}")
                                        if "prompt" in scene:
                                            st.write(f"**Prompt:** {scene.get('prompt', '')}")
                                else:
                                    # Display placeholder for missing images
                                    st.write(f"Scene {scene.get('scene_id', '?')} - No image available")
                                    if "error" in scene:
                                        st.error(scene["error"])
            
            # Add regenerate button
            if st.button("Regenerate Storyboard", key="regenerate_button", type="primary"):
                with st.spinner("Regenerating storyboard images..."):
                    try:
                        storyboard_results = asyncio.run(storyboard_coordinator.generate_storyboard(script_results))
                        save_to_storage(storyboard_results, 'storyboard_results.json')
                        st.success("Storyboard regenerated!")
                        st.rerun()
                    except Exception as e:
                        logger.error(f"Error regenerating storyboard: {str(e)}", exc_info=True)
                        st.error(f"An error occurred: {str(e)}")
            
            # Add download button
            if "saved_path" in storyboard_results:
                st.download_button(
                    label="Download Storyboard Data",
                    data=json.dumps(storyboard_results, indent=2),
                    file_name="storyboard_data.json",
                    mime="application/json"
                )
    
    with tab2:
        # Display formatted JSON
        if storyboard_results:
            st.json(storyboard_results)
        else:
            st.info("No storyboard data available. Generate a storyboard first.")
    
    with tab3:
        st.subheader("Storyboard Settings")
        st.write("Adjust these settings before generating a new storyboard:")
        
        # Storyboard appearance settings
        with st.expander("Visual Style", expanded=True):
            style = st.selectbox("Storyboard Style", ["Cinematic", "Sketch", "Comic", "Noir", "Animation"], index=0)
            aspect_ratio = st.selectbox("Aspect Ratio", ["16:9", "4:3", "1:1", "2.35:1"], index=0)
            color_scheme = st.selectbox("Color Scheme", ["Full Color", "Black & White", "Monochromatic", "Sepia"], index=0)
        
        # Layout settings
        with st.expander("Layout Settings"):
            panels_per_page = st.slider("Panels Per Page", min_value=1, max_value=9, value=6)
            include_captions = st.checkbox("Include Scene Captions", value=True)
            include_dialogue = st.checkbox("Include Key Dialogue", value=False)
        
        # Save settings button
        if st.button("Save Settings"):
            settings = {
                "visual_style": {
                    "style": style,
                    "aspect_ratio": aspect_ratio,
                    "color_scheme": color_scheme
                },
                "layout": {
                    "panels_per_page": panels_per_page,
                    "include_captions": include_captions,
                    "include_dialogue": include_dialogue
                }
            }
            save_to_storage(settings, 'storyboard_settings.json')
            st.success("Settings saved! They will be applied to the next storyboard generation.")

def show_overview():
    st.header("Project Overview")
    results = {
        'script': load_from_storage('script_ingestion_results.json'),
        'one_liner': load_from_storage('one_liner_results.json'),
        'characters': load_from_storage('character_breakdown_results.json'),
        'schedule': load_from_storage('schedule_results.json'),
        'budget': load_from_storage('budget_results.json'),
        'storyboard': load_from_storage('storyboard_results.json')
    }
    
    if all(results.values()):
        st.subheader("Script Analysis")
        st.json(results['script'])
        
        st.subheader("One-Liner")
        st.json(results['one_liner'])
        
        st.subheader("Character Breakdown")
        st.json(results['characters'])
        
        st.subheader("Production Schedule")
        st.json(results['schedule'])
        
        st.subheader("Budget")
        st.json(results['budget'])
        
        st.subheader("Storyboard")
        st.json(results['storyboard'])
    else:
        st.warning("Please complete all previous steps first.")

if __name__ == '__main__':
    logger.info("Application started")
    main() 